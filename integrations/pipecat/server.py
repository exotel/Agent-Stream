#!/usr/bin/env python3
"""
FastAPI WebSocket server for Exotel AgentStream + Pipecat.

Point Connect Voice AI StreamUrl at:
  wss://YOUR_HOST/ws?sample-rate=8000

Uses ExotelFrameSerializer:
  https://docs.pipecat.ai/api-reference/server/services/serializers/exotel
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from loguru import logger
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.exotel import ExotelFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from bot import run_bot
from greeting_cache import warm_greeting_cache
from voice_config import cartesia_voice_id, greeting_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await warm_greeting_cache()
    except Exception:
        logger.exception("Greeting warm failed — will fall back to live TTS")
    logger.info(
        "Pipecat Exotel bridge ready — WSS /ws "
        f"voice={cartesia_voice_id()} greeting={greeting_text()!r}"
    )
    yield


app = FastAPI(title="Agent-Stream Pipecat Exotel", lifespan=lifespan)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "ws": "/ws"})


@app.websocket("/ws")
async def exotel_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        transport_type, call_data = await parse_telephony_websocket(websocket)
        logger.info(f"telephony transport={transport_type} call_data={call_data}")

        stream_id = call_data.get("stream_id") or call_data.get("stream_sid")
        call_id = call_data.get("call_id") or call_data.get("call_sid")
        account_sid = call_data.get("account_sid") or os.getenv("EXOTEL_ACCOUNT_SID")

        serializer_kwargs = {
            "stream_sid": stream_id,
            "call_sid": call_id,
        }
        # Newer Pipecat accepts stream_id/call_id; try modern names first via explicit ctor
        try:
            serializer = ExotelFrameSerializer(
                stream_id=stream_id,
                call_id=call_id,
                account_sid=account_sid,
                api_key=os.getenv("EXOTEL_API_KEY"),
                api_token=os.getenv("EXOTEL_API_TOKEN"),
            )
        except TypeError:
            serializer = ExotelFrameSerializer(**serializer_kwargs)

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                serializer=serializer,
            ),
        )

        await run_bot(transport, handle_sigint=False)
    except Exception:
        logger.exception("Exotel WebSocket session failed")
        try:
            await websocket.close()
        except Exception:
            pass


def main() -> None:
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
