#!/usr/bin/env python3
"""
Print the Exotel WebSocket URL for manual use (e.g. paste in Exotel Voicebot Applet).
Your app must be running and reachable at the host you pass (e.g. ngrok host).

Usage:
  export WSS_HOST=abc123.ngrok-free.app   # or your deployed host
  python scripts/get_wss_url.py

  Or:
  python scripts/get_wss_url.py abc123.ngrok-free.app

  Optional: RUN_ID and NAME env vars, or use defaults.
"""
import os
import sys

# Path must match exotel.py: /sales-agent/exotel/ws/audio/{run_id}/{name}
SAMPLE_RATE = 16000
DEFAULT_RUN_ID = "manual-test-run"
DEFAULT_NAME = "TestUser"


def main():
    host = os.getenv("WSS_HOST") or os.getenv("BASE_URL", "").replace("https://", "").replace("http://", "").strip("/")
    if len(sys.argv) > 1:
        host = sys.argv[1].replace("https://", "").replace("http://", "").strip("/")
    if not host:
        print("Usage: set WSS_HOST or pass host as first argument.", file=sys.stderr)
        print("Example: WSS_HOST=abc123.ngrok-free.app python scripts/get_wss_url.py", file=sys.stderr)
        print("Or:     python scripts/get_wss_url.py abc123.ngrok-free.app", file=sys.stderr)
        sys.exit(1)

    run_id = os.getenv("RUN_ID", DEFAULT_RUN_ID)
    name = os.getenv("NAME", DEFAULT_NAME)

    wss = f"wss://{host}/sales-agent/exotel/ws/audio/{run_id}/{name}?sample-rate={SAMPLE_RATE}"
    print(wss)
    print("", file=sys.stderr)
    print("Use this URL in Exotel Voicebot Applet (or connect manually).", file=sys.stderr)
    print("Ensure your app is running and reachable at that host.", file=sys.stderr)


if __name__ == "__main__":
    main()
