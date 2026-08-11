"""Shared Cartesia voice settings for greeting cache and live TTS.

Keep greeting synthesis and turn TTS on the same voice / model / rate / encoding
so the caller hears one consistent agent voice. Values are read from the
environment at call time (after dotenv load).
"""

from __future__ import annotations

import os

# AgentStream telephony (fixed for Connect Voice AI)
SAMPLE_RATE = 8000
ENCODING = "pcm_s16le"
CONTAINER = "raw"

CARTESIA_VERSION = "2026-03-01"
CARTESIA_BYTES_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_WS_URL = "wss://api.cartesia.ai/tts/websocket"

_DEFAULT_VOICE = "71a7ad14-091c-4e8e-a314-022ece01c121"
_DEFAULT_GREETING = "Hi, how can I help?"


def cartesia_api_key() -> str:
    return os.getenv("CARTESIA_API_KEY", "")


def cartesia_model() -> str:
    return os.getenv("CARTESIA_MODEL", "sonic-3.5")


def cartesia_voice_id() -> str:
    return os.getenv("CARTESIA_VOICE_ID", _DEFAULT_VOICE)


def greeting_text() -> str:
    return os.getenv("PIPECAT_GREETING", _DEFAULT_GREETING)
