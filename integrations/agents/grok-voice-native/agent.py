"""Grok Voice (speech-to-speech) session for Exotel AgentStream.

Bridges Exotel PCM16 over WSS to xAI Realtime Voice:
  wss://api.x.ai/v1/realtime?model=<GROK_MODEL>

Docs: https://docs.x.ai/developers/model-capabilities/audio/voice-agent
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import websockets
from loguru import logger

from integrations.agents._shared.wss_server import AgentSession


def _xai_realtime_url() -> str:
    model = os.getenv("GROK_MODEL", "grok-voice-latest")
    return f"wss://api.x.ai/v1/realtime?model={model}"


class GrokVoiceSession(AgentSession):
    def __init__(self, stream_sid: str, sample_rate: int, call_meta: dict):
        super().__init__(stream_sid, sample_rate, call_meta)
        self._ws: Any = None
        self._reader: Optional[asyncio.Task] = None
        self._closed = False

    async def on_start(self) -> None:
        key = os.environ.get("XAI_API_KEY")
        if not key:
            logger.error("XAI_API_KEY is required for Grok Voice")
            return

        rate = self.sample_rate if self.sample_rate in (8000, 16000, 24000) else 8000
        voice = (os.getenv("GROK_VOICE") or "eve").lower()
        instructions = os.getenv(
            "SYSTEM_PROMPT",
            "You are a concise helpful phone assistant. Keep answers short.",
        )

        try:
            self._ws = await websockets.connect(
                _xai_realtime_url(),
                additional_headers={"Authorization": f"Bearer {key}"},
                max_size=8 * 1024 * 1024,
            )
        except TypeError:
            # websockets>=13 renamed additional_headers → extra_headers on some builds
            self._ws = await websockets.connect(
                _xai_realtime_url(),
                extra_headers={"Authorization": f"Bearer {key}"},
                max_size=8 * 1024 * 1024,
            )

        await self._ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "voice": voice,
                        "instructions": instructions,
                        "turn_detection": {
                            "type": "server_vad",
                            "silence_duration_ms": int(
                                os.getenv("GROK_SILENCE_MS", "600")
                            ),
                        },
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": rate}
                            },
                            "output": {
                                "format": {"type": "audio/pcm", "rate": rate}
                            },
                        },
                    },
                }
            )
        )
        self._reader = asyncio.create_task(self._read_xai())
        logger.info(
            f"Grok Voice connected stream={self.stream_sid} rate={rate} voice={voice}"
        )

        greeting = os.getenv("GREETING_TEXT", "Hello! How can I help you today?")
        await self._ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "force_message",
                        "role": "assistant",
                        "interruptible": False,
                        "content": [{"type": "output_text", "text": greeting}],
                    },
                }
            )
        )

    async def on_media(self, pcm: bytes) -> None:
        if not self._ws or self._closed or not pcm:
            return
        try:
            await self._ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm).decode("ascii"),
                    }
                )
            )
        except Exception:
            logger.exception("failed to append audio to Grok Voice")

    async def on_stop(self) -> None:
        self._closed = True
        if self._reader:
            self._reader.cancel()
            try:
                await self._reader
            except asyncio.CancelledError:
                pass
            self._reader = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        logger.info(f"Grok Voice session stopped stream={self.stream_sid}")

    async def _read_xai(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if self._closed:
                    break
                if isinstance(raw, (bytes, bytearray)):
                    await self.send_pcm(bytes(raw))
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_event(event)
        except asyncio.CancelledError:
            raise
        except websockets.ConnectionClosed as e:
            logger.warning(f"Grok Voice WS closed: {e}")
        except Exception:
            logger.exception("Grok Voice reader failed")

    async def _handle_event(self, event: dict) -> None:
        etype = event.get("type") or ""

        if etype in (
            "input_audio_buffer.speech_started",
            "input_audio_buffer.speech_started.delta",
        ):
            await self.clear_playback()
            return

        if etype in ("response.output_audio.delta", "response.audio.delta"):
            delta = event.get("delta") or event.get("audio") or ""
            if delta:
                await self.send_pcm(base64.b64decode(delta))
            return

        if etype == "error":
            logger.error(f"Grok Voice error: {event}")
            return

        if etype in ("session.updated", "response.done", "conversation.item.created"):
            logger.debug(f"Grok Voice event: {etype}")


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> GrokVoiceSession:
    return GrokVoiceSession(stream_sid, sample_rate, call_meta)
