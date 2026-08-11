# OpenAI Realtime + Exotel AgentStream

Speech-to-speech bot using **OpenAI Realtime API (GA)** over Exotel bidirectional WSS.

## Prerequisites

| Item | Notes |
|------|--------|
| Python 3.10+ | venv recommended |
| OpenAI | API key with Realtime access ([platform](https://platform.openai.com)) |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Public WSS | ngrok or cloudflared |
| Exotel env | `shared/.env.exotel` from [`shared/env.exotel.example`](../../shared/env.exotel.example) |

**Critical:** Always append `?sample-rate=8000` to StreamUrl. Default telephony rate is **8 kHz** (`audio/pcmu`). Missing query used to default to 24 kHz and caused low pitch on the phone.

## 3 steps + test call

### Step 1 — Install and configure

```bash
cd integrations/openai-realtime
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY
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
```

### Step 2 — Run the bot

```bash
# Corporate SSL tips (if needed):
# export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")

python main.py
```

Listen: `0.0.0.0:5000`. WebSocket path: `/` (root).

### Step 3 — Tunnel and place a Connect call

```bash
cloudflared tunnel --url http://127.0.0.1:5000
# or: ngrok http 5000

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

- Greeting at normal pitch (not slow/deep).
- Logs: `Audio Format: audio/pcmu → audio/pcmu`, `first_audio_ms=…`, `SESSION UPDATED`.
- Call duration ≫ 4s.

See [Connect Voice AI](../../docs/CONNECT_VOICE_AI.md) and [docs.exotel.com draft](../../docs/exotel-developer/openai-realtime.md).

## Notes

- GA Realtime: no `OpenAI-Beta: realtime=v1` header; nested `session.audio` config.
- Root shim: `python main.py` from repository root still works.
