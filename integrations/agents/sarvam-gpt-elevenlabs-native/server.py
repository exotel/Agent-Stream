#!/usr/bin/env python3
"""Exotel AgentStream server — sarvam-gpt-elevenlabs-native."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv

load_dotenv()

from agent import make_session
from integrations.agents._shared.wss_server import create_app, run_app

app = create_app(make_session, title="Sarvam + GPT + ElevenLabs (native pipeline)")

if __name__ == "__main__":
    run_app(app, default_port=8000)
