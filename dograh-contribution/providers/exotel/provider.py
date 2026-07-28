"""Exotel telephony provider for Dograh.

Outbound uses Exotel Connect Voice AI API:
https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api
"""

import json
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import aiohttp
from fastapi import HTTPException, Response
from loguru import logger

from api.enums import TelephonyCallStatus, WorkflowRunMode
from api.services.telephony.base import (
    CallInitiationResult,
    NormalizedInboundData,
    TelephonyProvider,
)
from api.utils.common import get_backend_endpoints

if TYPE_CHECKING:
    from fastapi import WebSocket

DEFAULT_API_BASE_URL = "https://api.in.exotel.com"


class ExotelProvider(TelephonyProvider):
    PROVIDER_NAME = WorkflowRunMode.EXOTEL.value
    WEBHOOK_ENDPOINT = "exotel"

    def __init__(self, config: Dict[str, Any]):
        self.account_sid = config.get("account_sid")
        self.api_key = config.get("api_key")
        self.api_token = config.get("api_token")
        self.api_base_url = (config.get("api_base_url") or DEFAULT_API_BASE_URL).rstrip(
            "/"
        )
        self.from_numbers = config.get("from_numbers", [])
        if isinstance(self.from_numbers, str):
            self.from_numbers = [self.from_numbers]

    def _auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self.api_key, self.api_token)

    def _calls_connect_url(self) -> str:
        return f"{self.api_base_url}/v1/Accounts/{self.account_sid}/Calls/connect.json"

    def _call_url(self, call_id: str) -> str:
        return (
            f"{self.api_base_url}/v1/Accounts/{self.account_sid}/Calls/{call_id}.json"
        )

    async def initiate_call(
        self,
        to_number: str,
        webhook_url: str,
        workflow_run_id: Optional[int] = None,
        from_number: Optional[str] = None,
        **kwargs: Any,
    ) -> CallInitiationResult:
        # webhook_url unused: Connect Voice AI attaches StreamUrl on dial.
        if not self.validate_config():
            raise ValueError("Exotel provider not properly configured")

        workflow_id = kwargs["workflow_id"]
        organization_id = kwargs["organization_id"]

        if from_number is None:
            if not self.from_numbers:
                raise ValueError(
                    "No phone numbers configured for Exotel. "
                    "Add at least one ExoPhone as CallerId."
                )
            from_number = random.choice(self.from_numbers)

        backend_endpoint, wss_backend_endpoint = await get_backend_endpoints()
        stream_url = (
            f"{wss_backend_endpoint}/api/v1/telephony/ws/"
            f"{workflow_id}/{organization_id}/{workflow_run_id}"
        )

        form: Dict[str, Any] = {
            "From": to_number,
            "CallerId": from_number,
            "StreamUrl": stream_url,
            "StreamType": "bidirectional",
        }
        if workflow_run_id:
            form["StatusCallback"] = (
                f"{backend_endpoint}/api/v1/telephony/exotel/"
                f"status-callback/{workflow_run_id}"
            )
            form["StatusCallbackEvents[]"] = "terminal"

        logger.info(
            f"[Exotel] Initiating call to={to_number} from={from_number} "
            f"run={workflow_run_id}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._calls_connect_url(), data=form, auth=self._auth()
            ) as response:
                body_text = await response.text()
                if response.status not in (200, 201):
                    logger.error(
                        f"[Exotel] Calls/connect failed HTTP {response.status}: "
                        f"{body_text}"
                    )
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Exotel Calls/connect failed: {body_text}",
                    )

                try:
                    response_data = json.loads(body_text)
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Exotel returned non-JSON response: {body_text[:200]}",
                    ) from e

        call = response_data.get("Call") or response_data
        call_id = str(call.get("Sid") or "")
        if not call_id:
            raise HTTPException(
                status_code=502,
                detail=f"Exotel response missing Call Sid: {response_data}",
            )

        return CallInitiationResult(
            call_id=call_id,
            status=str(call.get("Status") or "queued"),
            caller_number=from_number,
            provider_metadata={"call_id": call_id},
            raw_response=response_data,
        )

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Exotel provider not properly configured")

        async with aiohttp.ClientSession() as session:
            async with session.get(self._call_url(call_id), auth=self._auth()) as response:
                if response.status != 200:
                    error_data = await response.text()
                    raise Exception(f"Failed to get Exotel call status: {error_data}")
                return await response.json()

    async def get_available_phone_numbers(self) -> List[str]:
        return list(self.from_numbers)

    def validate_config(self) -> bool:
        return bool(self.account_sid and self.api_key and self.api_token)

    async def verify_webhook_signature(
        self, url: str, params: Dict[str, Any], signature: str
    ) -> bool:
        return True

    async def get_webhook_response(
        self, workflow_id: int, organization_id: int, workflow_run_id: int
    ) -> str:
        return ""

    async def get_call_cost(self, call_id: str) -> Dict[str, Any]:
        try:
            call_data = await self.get_call_status(call_id)
            call = call_data.get("Call") or call_data
            price = call.get("Price") or "0"
            duration = call.get("Duration") or 0
            return {
                "cost_usd": abs(float(price)) if price else 0.0,
                "duration": int(duration) if duration else 0,
                "status": call.get("Status") or "unknown",
                "raw_response": call_data,
            }
        except Exception as e:
            logger.error(f"Exception fetching Exotel call cost: {e}")
            return {"cost_usd": 0.0, "duration": 0, "status": "error", "error": str(e)}

    def parse_status_callback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        status_raw = data.get("Status") or data.get("CallStatus") or ""
        return {
            "call_id": data.get("CallSid") or data.get("Sid") or "",
            "status": TelephonyCallStatus.from_raw(status_raw) or status_raw,
            "from_number": data.get("From") or data.get("CallFrom"),
            "to_number": data.get("To") or data.get("CallTo"),
            "direction": data.get("Direction"),
            "duration": data.get("Duration"),
            "extra": data,
        }

    async def handle_websocket(
        self,
        websocket: "WebSocket",
        workflow_id: int,
        organization_id: int,
        workflow_run_id: int,
    ) -> None:
        from api.services.pipecat.run_pipeline import run_pipeline_telephony

        first_msg = await websocket.receive_text()
        msg = json.loads(first_msg)
        if msg.get("event") != "connected":
            logger.error(f"Expected 'connected' event, got: {msg.get('event')}")
            await websocket.close(code=4400, reason="Expected connected event")
            return

        start_msg = json.loads(await websocket.receive_text())
        if start_msg.get("event") != "start":
            logger.error("Expected 'start' event second")
            await websocket.close(code=4400, reason="Expected start event")
            return

        start = start_msg.get("start") or {}
        try:
            stream_sid = start["streamSid"]
            call_sid = start["callSid"]
        except KeyError:
            logger.error("Missing streamSid or callSid in Exotel start message")
            await websocket.close(code=4400, reason="Missing stream identifiers")
            return

        logger.info(
            f"[run {workflow_run_id}] Exotel WS stream_sid={stream_sid} "
            f"call_sid={call_sid}"
        )

        await run_pipeline_telephony(
            websocket,
            provider_name=self.PROVIDER_NAME,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            organization_id=organization_id,
            call_id=call_sid,
            transport_kwargs={"stream_sid": stream_sid, "call_sid": call_sid},
        )

    # Inbound is out of scope for Connect Voice AI (outbound) API.
    # For inbound: App Bazaar flow + Voicebot applet + assign ExoPhone.
    @classmethod
    def can_handle_webhook(
        cls, webhook_data: Dict[str, Any], headers: Dict[str, str]
    ) -> bool:
        return False

    @staticmethod
    def parse_inbound_webhook(webhook_data: Dict[str, Any]) -> NormalizedInboundData:
        return NormalizedInboundData(
            provider=ExotelProvider.PROVIDER_NAME,
            call_id="",
            from_number="",
            to_number="",
            direction="inbound",
            call_status="",
            account_id=None,
            raw_data=webhook_data,
        )

    @staticmethod
    def validate_account_id(config_data: dict, webhook_account_id: str) -> bool:
        return False

    async def verify_inbound_signature(
        self,
        url: str,
        webhook_data: Dict[str, Any],
        headers: Dict[str, str],
        body: str = "",
    ) -> bool:
        return False

    async def start_inbound_stream(
        self,
        *,
        websocket_url: str,
        workflow_run_id: int,
        normalized_data,
        backend_endpoint: str,
    ):
        return Response(
            content=json.dumps({"error": "Exotel inbound is not supported"}),
            media_type="application/json",
        )

    @staticmethod
    def generate_error_response(error_type: str, message: str) -> tuple:
        return Response(
            content=json.dumps({"error": message}),
            media_type="application/json",
        )

    async def transfer_call(
        self,
        destination: str,
        transfer_id: str,
        conference_name: str,
        timeout: int = 30,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raise NotImplementedError("Exotel provider does not support call transfers")

    def supports_transfers(self) -> bool:
        return False
