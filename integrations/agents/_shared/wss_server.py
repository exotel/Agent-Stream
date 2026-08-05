"""
FastAPI AgentStream WebSocket host for Exotel voice agent recipes.

Exotel connects to /ws?sample-rate=8000|16000|24000 and sends JSON events.
Your agent implements AgentSession (on_start / on_media / on_stop).
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger

from .media import b64_pcm_decode, clear_event, media_event, sample_rate_from_path


class AgentSession(ABC):
    """One phone call / stream."""

    def __init__(self, stream_sid: str, sample_rate: int, call_meta: Dict[str, Any]):
        self.stream_sid = stream_sid
        self.sample_rate = sample_rate
        self.call_meta = call_meta
        self._send: Optional[Callable] = None
        self._chunk = 0

    def bind_sender(self, send_json: Callable) -> None:
        self._send = send_json

    async def send_pcm(self, pcm: bytes) -> None:
        if not self._send or not pcm:
            return
        self._chunk += 1
        await self._send(media_event(self.stream_sid, pcm, self._chunk))

    async def clear_playback(self) -> None:
        if self._send:
            await self._send(clear_event(self.stream_sid))

    @abstractmethod
    async def on_start(self) -> None: ...

    @abstractmethod
    async def on_media(self, pcm: bytes) -> None: ...

    @abstractmethod
    async def on_stop(self) -> None: ...


SessionFactory = Callable[[str, int, Dict[str, Any]], AgentSession]


def create_app(session_factory: SessionFactory, *, title: str = "Exotel Voice Agent") -> FastAPI:
    app = FastAPI(title=title)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "ws": "/ws"})

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        sample_rate = sample_rate_from_path(str(websocket.url), default=8000)
        session: Optional[AgentSession] = None
        stream_sid = "unknown"

        async def send_json(payload: dict) -> None:
            await websocket.send_text(json.dumps(payload))

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event = data.get("event") or data.get("Event")
                if event == "connected":
                    logger.info("AgentStream connected")
                    continue

                if event == "start":
                    start = data.get("start") or data
                    stream_sid = (
                        data.get("streamSid")
                        or start.get("streamSid")
                        or start.get("stream_sid")
                        or f"stream-{id(websocket)}"
                    )
                    session = session_factory(stream_sid, sample_rate, dict(start))
                    session.bind_sender(send_json)
                    logger.info(f"start stream={stream_sid} rate={sample_rate}")
                    await session.on_start()
                    continue

                if event == "media" and session:
                    media = data.get("media") or {}
                    payload = media.get("payload") or media.get("Payload")
                    if payload:
                        await session.on_media(b64_pcm_decode(payload))
                    continue

                if event in ("stop", "closed") and session:
                    await session.on_stop()
                    session = None
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected stream={stream_sid}")
        except Exception:
            logger.exception("AgentStream session error")
        finally:
            if session:
                try:
                    await session.on_stop()
                except Exception:
                    pass

    return app


def run_app(app: FastAPI, *, default_port: int = 8000) -> None:
    import uvicorn

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", str(default_port)))
    uvicorn.run(app, host=host, port=port)
