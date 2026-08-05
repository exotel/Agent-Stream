"""Grok Voice session scaffold for Exotel AgentStream.

Wire xAI realtime voice WebSocket here. Until connected, the WSS path accepts
AgentStream media and logs session lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from loguru import logger

from integrations.agents._shared.wss_server import AgentSession


class GrokVoiceSession(AgentSession):
    async def on_start(self) -> None:
        logger.info(
            "Grok Voice session started — set XAI_API_KEY and implement realtime "
            "voice WS bridge in agent.py (see recipe README)."
        )

    async def on_media(self, pcm: bytes) -> None:
        return

    async def on_stop(self) -> None:
        logger.info("Grok Voice session stopped")


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> GrokVoiceSession:
    return GrokVoiceSession(stream_sid, sample_rate, call_meta)
