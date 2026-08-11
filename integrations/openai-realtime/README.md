# OpenAI Realtime + Exotel AgentStream

Speech-to-speech bot using **OpenAI Realtime API (GA)** over Exotel bidirectional WSS.

This is a **working sample** suitable to harden for production (paced media, no secrets in git). It is **not** a multi-tenant autoscaling worker by itself.

Canonical path: [`integrations/openai-realtime`](https://github.com/exotel/Agent-Stream/tree/main/integrations/openai-realtime).

```text
integrations/openai-realtime/
  main.py           # entry
  config.py
  requirements.txt
  .env.example      # copy to .env (gitignored)
  README.md
  core/
    bot.py          # Exotel ↔ OpenAI bridge
    __init__.py
```

## Prerequisites

| Item | Notes |
|------|--------|
| Python 3.10+ | venv recommended; on 3.13+ `audioop-lts` comes via requirements |
| OpenAI | API key with Realtime access ([platform](https://platform.openai.com)) |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Public WSS | ngrok or cloudflared |
| Exotel env | `shared/.env.exotel` from [`shared/env.exotel.example`](../../shared/env.exotel.example) |

**Critical:** Always append `?sample-rate=8000` to StreamUrl. Exotel telephony is **8 kHz PCM**. The bridge negotiates **PCM 24 kHz** with OpenAI and resamples locally.

## 3 steps + test call

### Step 1 — Install and configure

```bash
cd integrations/openai-realtime
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY only in .env — never commit it
```

Suggested `.env`:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-realtime
OPENAI_VOICE=coral
SAMPLE_RATE=8000
DEFAULT_SAMPLE_RATE=8000
SERVER_PORT=5000
COMPANY_NAME=Exotel
SALES_BOT_NAME=Sara
# SEND_TEST_TONE=true   # debug only — beep before greeting (default: off)
```

### Step 2 — Run the bot

```bash
python main.py
```

Listen: `0.0.0.0:5000`. WebSocket path: `/` (root).

### Step 3 — Tunnel and place a Connect call

```bash
cloudflared tunnel --url http://127.0.0.1:5000

# From repo root
set -a && source shared/.env.exotel && set +a
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/?sample-rate=8000"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/?sample-rate=8000` |
| **Port** | `5000` |

### Verify

- No beep before greeting (`SEND_TEST_TONE` defaults to false).
- Greeting at normal pitch.
- Logs: `Audio Format: audio/pcm → audio/pcm`, `SESSION UPDATED`, `first_audio_ms=…`, outbound ~100 ms paced frames.

See [Connect Voice AI](../../docs/CONNECT_VOICE_AI.md).

## Audio / security notes

- **No secrets in git** — only `.env.example`; real keys live in local `.env` / `shared/.env.exotel` (gitignored).
- **No test tone by default** — `SEND_TEST_TONE=true` for pipeline debug only.
- **Outbound pacing** — PCM 24→8 kHz, buffered, ~100 ms frames, monotonic sequence + elapsed timestamp.
- GA Realtime: no `OpenAI-Beta` header; nested `session.audio`.
- Root shim: `python main.py` from repository root still works.
