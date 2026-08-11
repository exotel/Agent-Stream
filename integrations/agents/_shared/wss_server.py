"""
FastAPI AgentStream WebSocket host for Exotel voice agent recipes.

Exotel connects to /ws?sample-rate=8000|16000|24000 and sends JSON events.
Your agent implements AgentSession (on_start / on_media / on_stop).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
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
        self._t0 = time.monotonic()
        self._bytes_out = 0
        self._frames_out = 0
        self._media_in = 0
        self._first_audio_logged = False

    def bind_sender(self, send_json: Callable) -> None:
        self._send = send_json

    async def send_pcm(self, pcm: bytes) -> None:
        """Stream PCM16 to Exotel as paced frames (AgentStream-safe).

        Exotel Voicebot docs: chunk multiples of 320 bytes; payloads >100KB risk
        timeouts. Dumping the whole greeting as one WSS message (or blasting
        frames with sleep(0)) correlates with short ~4s Connect hangups.
        Pace near realtime from a background task so the receive loop stays free.
        """
        if not self._send or not pcm:
            return
        # Prefer ~100ms frames (3200 B @ 8 kHz) — Exotel's documented sweet spot.
        frame = max(320, int(self.sample_rate * 0.1) * 2)
        # Keep multiple of 320 bytes
        frame = max(320, (frame // 320) * 320)
        frame_sec = (frame / 2) / max(self.sample_rate, 1)
        if len(pcm) % 2:
            pcm = pcm[:-1]
        offset = 0
        started = time.monotonic()
        while offset < len(pcm):
            chunk = pcm[offset : offset + frame]
            offset += len(chunk)
            if len(chunk) < 2:
                break
            # Pad final short frame to 320-byte alignment when needed
            if len(chunk) % 320 and offset >= len(pcm):
                pad = 320 - (len(chunk) % 320)
                chunk = chunk + (b"\x00" * pad)
            self._chunk += 1
            self._frames_out += 1
            self._bytes_out += len(chunk)
            elapsed_ms = int((time.monotonic() - self._t0) * 1000)
            if not self._first_audio_logged:
                self._first_audio_logged = True
                logger.info(
                    f"first_audio_ms={elapsed_ms} stream={self.stream_sid} "
                    f"rate={self.sample_rate}"
                )
            await self._send(
                media_event(
                    self.stream_sid,
                    chunk,
                    self._chunk,
                    timestamp_ms=elapsed_ms,
                    sequence_number=self._chunk,
                )
            )
            # Pace slightly under realtime; yield so Exotel media keeps flowing.
            await asyncio.sleep(frame_sec * 0.9)
        took = (time.monotonic() - started) * 1000
        audio_ms = (len(pcm) / 2) / max(self.sample_rate, 1) * 1000
        logger.info(
            f"send_pcm done stream={self.stream_sid} frames={self._frames_out} "
            f"bytes={self._bytes_out} audio_ms={audio_ms:.0f} wall_ms={took:.0f}"
        )

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

        t_conn = time.monotonic()
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
                        or data.get("stream_sid")
                        or start.get("streamSid")
                        or start.get("stream_sid")
                        or f"stream-{id(websocket)}"
                    )
                    call_sid = start.get("callSid") or start.get("call_sid") or ""
                    session = session_factory(stream_sid, sample_rate, dict(start))
                    session.bind_sender(send_json)
                    logger.info(
                        f"start stream={stream_sid} call={call_sid} rate={sample_rate}"
                    )
                    await session.on_start()
                    continue

                if event == "media" and session:
                    media = data.get("media") or {}
                    payload = media.get("payload") or media.get("Payload")
                    if payload:
                        session._media_in += 1
                        if session._media_in == 1 or session._media_in % 50 == 0:
                            logger.info(
                                f"recv media stream={stream_sid} "
                                f"n_in={session._media_in} n_out={session._frames_out}"
                            )
                        await session.on_media(b64_pcm_decode(payload))
                    continue

                if event in ("stop", "closed") and session:
                    age = time.monotonic() - t_conn
                    logger.info(
                        f"{event} stream={stream_sid} age_s={age:.1f} "
                        f"media_in={session._media_in} frames_out={session._frames_out} "
                        f"bytes_out={session._bytes_out}"
                    )
                    await session.on_stop()
                    session = None
                    break

        except WebSocketDisconnect:
            age = time.monotonic() - t_conn
            if session:
                logger.warning(
                    f"WebSocket disconnected stream={stream_sid} age_s={age:.1f} "
                    f"media_in={session._media_in} frames_out={session._frames_out} "
                    f"bytes_out={session._bytes_out}"
                )
            else:
                logger.warning(
                    f"WebSocket disconnected stream={stream_sid} age_s={age:.1f} (no session)"
                )
        except Exception:
            logger.exception("AgentStream session error")
        finally:
            if session:
                try:
                    age = time.monotonic() - t_conn
                    logger.info(
                        f"cleanup stream={stream_sid} age_s={age:.1f} "
                        f"media_in={session._media_in} frames_out={session._frames_out}"
                    )
                    await session.on_stop()
                except Exception:
                    pass

    return app


def run_app(app: FastAPI, *, default_port: int = 8000) -> None:
    import uvicorn

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", str(default_port)))
    uvicorn.run(app, host=host, port=port)
