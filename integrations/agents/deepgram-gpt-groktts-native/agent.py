"""Agent session for deepgram-gpt-groktts-native.

Grok TTS is implemented here with the documented xAI REST shape
(``voice_id`` + ``language`` + ``output_format``) instead of the
shared ``tts_grok`` helper, which uses an incomplete request body.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx
from dotenv import load_dotenv

load_dotenv()

from integrations.agents._shared.pipeline_agent import PipelineSession
from integrations.agents._shared.providers import stt_deepgram, llm_openai


async def tts_grok_rest(text: str, sample_rate: int) -> bytes:
    """xAI Text-to-Speech REST → raw PCM16 at the call sample rate.

    Docs: https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
    """
    key = os.environ["XAI_API_KEY"]
    voice = (os.getenv("GROK_TTS_VOICE") or os.getenv("GROK_VOICE") or "eve").lower()
    language = os.getenv("GROK_TTS_LANGUAGE", "en")
    rate = sample_rate if sample_rate in (8000, 16000, 24000) else 16000

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.x.ai/v1/tts",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "voice_id": voice,
                "language": language,
                "output_format": {
                    "codec": "pcm",
                    "sample_rate": rate,
                },
            },
        )
        r.raise_for_status()
        return r.content


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> PipelineSession:
    return PipelineSession(
        stream_sid,
        sample_rate,
        call_meta,
        stt=stt_deepgram,
        llm=llm_openai,
        tts=tts_grok_rest,
    )
