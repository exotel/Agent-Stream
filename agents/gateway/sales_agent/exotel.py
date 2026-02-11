import os
import json
from urllib.parse import urlencode, parse_qs, unquote_plus
import xml.etree.ElementTree as ET
import requests
from fastapi import APIRouter, Request, Depends, Response, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect

from app.core.security import verify_api_key
from app.core.utils import LoggerFactory

from agents.gateway.utils import OutgoingCall
from agents.gateway import getAppState, AppState
from agents.gateway.sales_agent.converstation import GeminiVoiceAgent

logger = LoggerFactory().get_logger()

EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN")
EXOTEL_SID = os.getenv("EXOTEL_SID")
EXOTEL_SALES_AGENT_APP_ID = os.getenv("EXOTEL_SALES_AGENT_APP_ID")
EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID")

# Exotel WebSocket URL template (requires basic auth in URL)

WEBSOCKET_URL_TEMPLATE = "wss://{hostname}/sales-agent/exotel/ws/audio" # exotel requires basic auth for websocket

# Exotel event constants
EXOTEL_EVENT_CONNECTED = "connected"
EXOTEL_EVENT_START = "start"
EXOTEL_EVENT_MEDIA = "media"
EXOTEL_EVENT_MARK = "mark"
EXOTEL_EVENT_CLEAR = "clear"
EXOTEL_EVENT_STOP = "stop"

DEFAULT_SAMPLE_RATE = 16000

router = APIRouter(tags=["exotel"],prefix="/exotel")

@router.post("/start-call", status_code=202)
async def make_outbound_call(
        call_request: OutgoingCall, request: Request,
        api_key: str = Depends(verify_api_key)
    ):
        redis_client = getAppState().resources.get("redis")
        if not redis_client:
            raise HTTPException(status_code=500, detail="Redis client not configured")
        
        try:
            # test without params first 
            # max 3 params can be added with total 256 chars
            params = urlencode(
                {
                    "run_id": call_request.run_id,
                    "name": call_request.name,
                }
            )
            EXOTEL_URL = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}/Calls/connect"
            
            data = {
                "From": call_request.mobile,
                "CallerId": EXOTEL_CALLER_ID,
                "Url": f"http://my.exotel.com/{EXOTEL_SID}/exoml/start_voice/{EXOTEL_SALES_AGENT_APP_ID}",
                "TimeLimit": 900, # 15 minutes
                "TimeOut": 25, # rings until 25 seconds
                # "StatusCallback": None # add the hangup url
                "CustomField": params
            }

            response = requests.post(
                EXOTEL_URL,
                params=params,
                data=data,
                # headers={
                #     "Content-Type": "application/json"
                # }
            ) 
            response.raise_for_status()

            content = response.content.decode('utf-8')
            if content:
                root = ET.fromstring(content)
                
                # Check for TwilioResponse wrapper which Exotel uses
                if root.tag == 'TwilioResponse':
                    call_element = root.find('Call')
                    if call_element is not None:
                        status = call_element.findtext("Status")
                        call_sid = call_element.findtext("Sid")
                    else:
                        status = None
                        call_sid = None
                else:
                    status = root.findtext("Status") 
                    call_sid = root.findtext("Sid")
                
                print(f"Exotel Response - Status: {status}, Sid: {call_sid}")

                if status in ["in-progress", "queued", "ringing"] and call_sid:
                    phone_key = f"sales-agent:call:{call_sid}:phone"
                    await redis_client.set(phone_key, call_request.run_id, ex=7200)
                    
                    return JSONResponse(content={
                        "status": "INITIATED",
                        "run_id": call_request.run_id,
                        "call_sid": call_sid,
                        "exotel_message": status
                    })

        except Exception as e:
            logger.error(f"Error making outbound call: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error making outbound call: {str(e)}")

@router.api_route("/handle-answered-calls",response_class=Response, methods=["GET","POST"])
async def handle_answered_calls(request: Request):
    # Use this call to decide the websocket url to use as per future applications
    try:
        cf = request.query_params.get("CustomField")
        query_parms = parse_qs(unquote_plus(cf))
        run_id = query_parms.get("run_id")[0]
        name = query_parms.get("name")[0]

        # Exotel Voicebot Applet expects sample rate as query param (docs use `sample-rate`).
        websocket_url = WEBSOCKET_URL_TEMPLATE.format(hostname=request.url.hostname) + f"/{run_id}/{name}?sample-rate={DEFAULT_SAMPLE_RATE}"
        return JSONResponse(content={"url" : websocket_url})
    except Exception as e:
        logger.error(f"Error handling answered calls: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error handling answered calls: {str(e)}")


@router.websocket("/ws/audio/{run_id}/{name}")
async def handle_media_stream(websocket: WebSocket, run_id: str, name: str):
    """
    WebSocket endpoint for Exotel bidirectional audio streaming with Gemini integration.
    Handles audio streaming between Exotel and Gemini Live API.
    """
    stream_sid = None
    gemini_agent = None

    try:
        # Accept WebSocket connection
        await websocket.accept()
        logger.info(f"📞 Exotel WebSocket connection accepted - run_id: {run_id}, name: {name}")

        # Initialize Gemini Voice Agent
        gemini_agent = GeminiVoiceAgent(getAppState().resources.get("redis"))
        # Force end-to-end sample rate if provided on the WebSocket URL.
        # Example: ?sample-rate=16000
        try:
            sr = websocket.query_params.get("sample-rate")
            if sr:
                sr_i = int(sr)
                if sr_i in (8000, 16000, 24000):
                    gemini_agent.forced_sample_rate = sr_i
                    gemini_agent.default_sample_rate = sr_i
                    logger.info(f"🎚️ Forcing end-to-end sample rate to {sr_i}Hz for run_id={run_id}, name={name}")
                else:
                    logger.warning(f"⚠️ Ignoring unsupported sample-rate={sr} (supported: 8000/16000/24000)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse sample-rate query param: {e}")

        # Handle the WebSocket connection using the GeminiVoiceAgent
        await gemini_agent.handle_exotel_websocket(websocket, path=None, run_id=run_id, name=name)

    except WebSocketDisconnect:
        logger.info(f"🔚 Exotel WebSocket disconnected: run_id={run_id}")

    except Exception as e:
        logger.error(f"❌ Error in Exotel WebSocket handler: {e}", exc_info=True)

    finally:
        # Cleanup handled by GeminiVoiceAgent.cleanup_connections()
        logger.info(f"🧹 Cleaned up Exotel WebSocket connection")


@router.get("/hangup-call", status_code=200)
async def exotel_hangup_webhook(
    request: Request,
    app_state: AppState = Depends(getAppState)
):
    """Exotel webhook when a call ends. Logs and clears Redis key; bridge does not use Mongo/Kafka."""
    try:
        data = dict(request.query_params)
        call_sid = data.get("CallSid")
        call_status = data.get("Stream[Status]")
        duration = data.get("Stream[Duration]")
        logger.info(f"📞 Exotel hangup: CallSid={call_sid}, Status={call_status}, Duration={duration}")

        redis_client = app_state.resources.get("redis")
        if redis_client and call_sid:
            phone_key = f"sales-agent:call:{call_sid}:phone"
            await redis_client.delete(phone_key)

        return {"status": "ok", "message": "Hangup processed"}

    except Exception as e:
        logger.error(f"❌ Error processing hangup webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
