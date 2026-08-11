#!/usr/bin/env python3
"""Sarvam STT+TTS echo bot for Exotel AgentStream (Connect Voice AI).

Run:
  export SARVAM_API_KEY=...
  python server.py

StreamUrl:
  wss://HOST/ws?sample-rate=8000
"""
from __future__ import annotations

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from integrations.agents._shared.pipeline_agent import (
    PipelineSession,
    cache_greeting_pcm,
)
from integrations.agents._shared.wss_server import create_app, run_app
from integrations.sarvam.sarvam_agentstream_pipeline import (
    synthesize_sarvam,
    transcribe_sarvam,
)

_pool = ThreadPoolExecutor(max_workers=4)


async def stt(pcm: bytes, sample_rate: int) -> str:
    key = os.environ["SARVAM_API_KEY"]
    loop = asyncio.get_running_loop()
    text, limited = await loop.run_in_executor(
        _pool, lambda: transcribe_sarvam(pcm, sample_rate, key)
    )
    return "" if limited else text


async def llm(text: str) -> str:
    return f"I heard you say: {text}" if text else "I did not catch that."


async def tts(text: str, sample_rate: int) -> bytes:
    key = os.environ["SARVAM_API_KEY"]
    rate = sample_rate if sample_rate in (8000, 16000, 24000) else 8000
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _pool,
        lambda: synthesize_sarvam(text, key, "en-IN", output_sample_rate=rate),
    )


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> PipelineSession:
    return PipelineSession(
        stream_sid,
        sample_rate,
        call_meta,
        stt=stt,
        llm=llm,
        tts=tts,
    )


def _warmup_greeting() -> None:
    """Pre-synthesize greeting so first_audio_ms stays under ~1s after start."""
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key:
        return
    greeting = os.environ.get(
        "GREETING_TEXT",
        "Namaste! Please say something after the beep.",
    )
    rate = int(os.environ.get("SAMPLE_RATE", "8000"))
    if rate not in (8000, 16000, 24000):
        rate = 8000
    logger.info(f"Warming greeting cache rate={rate}…")
    pcm = synthesize_sarvam(greeting, key, "en-IN", output_sample_rate=rate)
    cache_greeting_pcm(greeting, rate, pcm)
    ms = (len(pcm) / 2) / rate * 1000
    logger.info(f"Greeting cache ready bytes={len(pcm)} audio_ms={ms:.0f}")


app = create_app(make_session, title="Sarvam AgentStream echo")

if __name__ == "__main__":
    if not os.environ.get("SARVAM_API_KEY"):
        raise SystemExit("Set SARVAM_API_KEY")
    os.environ.setdefault(
        "GREETING_TEXT",
        "Namaste! Please say something after the beep.",
    )
    os.environ.setdefault("SAMPLE_RATE", "8000")
    _warmup_greeting()
    run_app(app, default_port=int(os.environ.get("SERVER_PORT", "8000")))
