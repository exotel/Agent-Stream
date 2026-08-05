#!/usr/bin/env python3
"""Place an outbound call via Exotel Connect Voice AI API.

Smoke-tests Calls/connect without Dograh. Point --stream-url at any
AgentStream WSS (this repo's bot, or Dograh telephony WS).

Docs: https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api

Env (or flags):
  EXOTEL_ACCOUNT_SID
  EXOTEL_API_KEY
  EXOTEL_API_TOKEN
  EXOTEL_CALLER_ID   ExoPhone in E.164
  EXOTEL_API_BASE_URL  default https://api.in.exotel.com
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from base64 import b64encode


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--to", required=True, help="Callee number (E.164)")
    p.add_argument(
        "--caller-id",
        default=os.environ.get("EXOTEL_CALLER_ID"),
        help="ExoPhone / CallerId",
    )
    p.add_argument(
        "--stream-url",
        default=os.environ.get(
            "EXOTEL_STREAM_URL", "wss://localhost:5000/ws"
        ),
        help="AgentStream WSS URL",
    )
    p.add_argument(
        "--status-callback",
        default=os.environ.get("EXOTEL_STATUS_CALLBACK"),
        help="Optional StatusCallback URL",
    )
    p.add_argument(
        "--account-sid",
        default=os.environ.get("EXOTEL_ACCOUNT_SID"),
    )
    p.add_argument("--api-key", default=os.environ.get("EXOTEL_API_KEY"))
    p.add_argument("--api-token", default=os.environ.get("EXOTEL_API_TOKEN"))
    p.add_argument(
        "--api-base-url",
        default=os.environ.get("EXOTEL_API_BASE_URL", "https://api.in.exotel.com"),
    )
    args = p.parse_args()

    missing = [
        n
        for n, v in [
            ("--caller-id / EXOTEL_CALLER_ID", args.caller_id),
            ("--account-sid / EXOTEL_ACCOUNT_SID", args.account_sid),
            ("--api-key / EXOTEL_API_KEY", args.api_key),
            ("--api-token / EXOTEL_API_TOKEN", args.api_token),
        ]
        if not v
    ]
    if missing:
        print("Missing: " + ", ".join(missing), file=sys.stderr)
        return 2

    base = args.api_base_url.rstrip("/")
    url = f"{base}/v1/Accounts/{args.account_sid}/Calls/connect.json"

    # application/x-www-form-urlencoded body
    fields = [
        ("From", args.to),
        ("CallerId", args.caller_id),
        ("StreamUrl", args.stream_url),
        ("StreamType", "bidirectional"),
    ]
    if args.status_callback:
        fields.append(("StatusCallback", args.status_callback))
        fields.append(("StatusCallbackEvents[]", "terminal"))

    from urllib.parse import urlencode

    body = urlencode(fields).encode("utf-8")
    auth = b64encode(f"{args.api_key}:{args.api_token}".encode()).decode()
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    print(f"POST {url}")
    print(f"  From={args.to} CallerId={args.caller_id}")
    print(f"  StreamUrl={args.stream_url}")

    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            print(f"HTTP {resp.status}")
            try:
                print(json.dumps(json.loads(raw), indent=2))
            except json.JSONDecodeError:
                print(raw)
            return 0
    except HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        return 1
    except URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
