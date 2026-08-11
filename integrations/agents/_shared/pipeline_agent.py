"""
Minimal turn-based STT → LLM → TTS session for AgentStream recipes.

Buffers caller PCM until silence gap, runs STT, LLM, TTS, then plays PCM back.
Not a full production VAD stack — tune or swap for Silero in production.
"""

from __future__ import annotations

import asyncio
import audioop
import os
import time
from typing import Awaitable, Callable, Optional

from loguru import logger

from .wss_server import AgentSession

STTFn = Callable[[bytes, int], Awaitable[str]]
LLMFn = Callable[[str], Awaitable[str]]
TTSFn = Callable[[str, int], Awaitable[bytes]]

# Process-level greeting cache: (text, sample_rate) -> pcm
_GREETING_CACHE: dict[tuple[str, int], bytes] = {}


def cache_greeting_pcm(text: str, sample_rate: int, pcm: bytes) -> None:
    """Store pre-synthesized greeting for TTFA under 1s on call start."""
    _GREETING_CACHE[(text, sample_rate)] = pcm


def get_cached_greeting_pcm(text: str, sample_rate: int) -> Optional[bytes]:
    return _GREETING_CACHE.get((text, sample_rate))


class PipelineSession(AgentSession):
    def __init__(
        self,
        stream_sid: str,
        sample_rate: int,
        call_meta: dict,
        *,
        stt: STTFn,
        llm: LLMFn,
        tts: TTSFn,
        silence_ms: int = 700,
        min_speech_ms: int = 400,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(stream_sid, sample_rate, call_meta)
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._silence_ms = silence_ms
        self._min_speech_bytes = int(sample_rate * 2 * (min_speech_ms / 1000.0))
        self._buf = bytearray()
        self._last_voice = time.monotonic()
        self._busy = False
        self._history: list[dict] = []
        self._system = system_prompt or os.getenv(
            "SYSTEM_PROMPT",
            "You are a concise helpful phone assistant. Keep answers short.",
        )
        self._watcher: Optional[asyncio.Task] = None

    async def on_start(self) -> None:
        self._watcher = asyncio.create_task(self._watch_silence())
        greeting = os.getenv("GREETING_TEXT", "Hello! How can I help you today?")
        # Off the receive-loop critical path; prefer process-boot cache for TTFA.
        self._greeting_task = asyncio.create_task(self._play_greeting(greeting))

    async def _play_greeting(self, greeting: str) -> None:
        try:
            t0 = time.monotonic()
            cached = get_cached_greeting_pcm(greeting, self.sample_rate)
            if cached:
                pcm = cached
                tts_ms = 0.0
                logger.info(
                    f"greeting cache hit rate={self.sample_rate} bytes={len(pcm)}"
                )
            else:
                pcm = await self._tts(greeting, self.sample_rate)
                tts_ms = (time.monotonic() - t0) * 1000
                cache_greeting_pcm(greeting, self.sample_rate, pcm)
            audio_ms = (len(pcm) / 2) / max(self.sample_rate, 1) * 1000
            logger.info(
                f"greeting ready tts_ms={tts_ms:.0f} audio_ms={audio_ms:.0f} bytes={len(pcm)}"
            )
            await self.send_pcm(pcm)
            logger.info("greeting playback queued")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("greeting TTS failed")

    async def on_media(self, pcm: bytes) -> None:
        if self._busy or not pcm:
            return
        # crude energy gate
        try:
            rms = audioop.rms(pcm, 2)
        except Exception:
            rms = 0
        if rms > int(os.getenv("VAD_RMS_THRESHOLD", "400")):
            self._buf.extend(pcm)
            self._last_voice = time.monotonic()

    async def on_stop(self) -> None:
        if getattr(self, "_greeting_task", None):
            self._greeting_task.cancel()
            try:
                await self._greeting_task
            except asyncio.CancelledError:
                pass
            self._greeting_task = None
        if self._watcher:
            self._watcher.cancel()

    async def _watch_silence(self) -> None:
        while True:
            await asyncio.sleep(0.1)
            if self._busy or not self._buf:
                continue
            gap = (time.monotonic() - self._last_voice) * 1000
            if gap >= self._silence_ms and len(self._buf) >= self._min_speech_bytes:
                pcm = bytes(self._buf)
                self._buf.clear()
                await self._handle_turn(pcm)

    async def _handle_turn(self, pcm: bytes) -> None:
        self._busy = True
        try:
            await self.clear_playback()
            text = (await self._stt(pcm, self.sample_rate)).strip()
            if not text:
                return
            logger.info(f"user: {text}")
            self._history.append({"role": "user", "content": text})
            reply = (await self._llm_with_history()).strip()
            logger.info(f"agent: {reply}")
            self._history.append({"role": "assistant", "content": reply})
            out = await self._tts(reply, self.sample_rate)
            await self.send_pcm(out)
        except Exception:
            logger.exception("pipeline turn failed")
        finally:
            self._busy = False

    async def _llm_with_history(self) -> str:
        # Adapter receives last user text only; recipes can wrap richer context
        last = self._history[-1]["content"] if self._history else ""
        return await self._llm(last)
