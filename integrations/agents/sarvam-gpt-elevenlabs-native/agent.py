"""Agent session for sarvam-gpt-elevenlabs-native."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv

load_dotenv()

from integrations.agents._shared.pipeline_agent import PipelineSession
from integrations.agents._shared.providers import stt_sarvam, llm_openai, tts_elevenlabs


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> PipelineSession:
    return PipelineSession(
        stream_sid,
        sample_rate,
        call_meta,
        stt=stt_sarvam,
        llm=llm_openai,
        tts=tts_elevenlabs,
    )
