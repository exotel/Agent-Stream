#!/usr/bin/env python3
"""Smoke-test Cartesia Line agent WebSocket (no Exotel).

Usage:
  export CARTESIA_API_KEY=sk_car_...
  export CARTESIA_AGENT_ID=agent_...
  python test_ws_connection.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# Allow importing agent helpers when run from this folder
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import (  # noqa: E402
    DEFAULT_AGENT_ID,
    CARTESIA_VERSION_WS,
    CARTESIA_WS_BASE,
    _connect_kwargs,
    fetch_agent_access_token,
)
import websockets  # noqa: E402


async def main() -> int:
    api_key = os.getenv("CARTESIA_API_KEY", "").strip()
    agent_id = os.getenv("CARTESIA_AGENT_ID", "").strip() or DEFAULT_AGENT_ID
    if not api_key:
        print("CARTESIA_API_KEY required", file=sys.stderr)
        return 2

    token = await fetch_agent_access_token(api_key)
    url = f"{CARTESIA_WS_BASE.rstrip('/')}/agents/stream/{agent_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Cartesia-Version": CARTESIA_VERSION_WS,
    }
    print(f"Connecting {url}")
    async with websockets.connect(
        url, open_timeout=30, **_connect_kwargs(headers)
    ) as ws:
        await ws.send(
            json.dumps(
                {
                    "event": "start",
                    "stream_id": "cli-smoke",
                    "config": {
                        "input_format": "mulaw_8000",
                        "output_audio_delivery": "as_available",
                    },
                    "metadata": {"from": "cli", "to": "smoke"},
                }
            )
        )
        for _ in range(20):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=20)
            except asyncio.TimeoutError:
                print("timeout waiting for events")
                break
            data = json.loads(raw)
            ev = data.get("event")
            if ev == "media_output":
                n = len((data.get("media") or {}).get("payload") or "")
                print(f"media_output b64_len={n}")
            elif ev == "turn_output_text_delta":
                print("delta:", repr((data.get("turn_output_text_delta") or {}).get("text")))
            else:
                slim = {k: v for k, v in data.items() if k != "media"}
                print("event:", json.dumps(slim)[:500])
        await ws.close(1000, "session completed")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
