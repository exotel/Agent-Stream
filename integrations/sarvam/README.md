# Sarvam AI + Exotel AgentStream

Indian-language STT/TTS (**Saaras** / **Bulbul**) over Exotel AgentStream WSS.

| File | Purpose |
|------|---------|
| [`server.py`](server.py) | Runnable echo bot (Connect Voice AI) |
| [`sarvam_agentstream_pipeline.py`](sarvam_agentstream_pipeline.py) | STT/TTS helpers |
| [`SARVAM_AGENTSTREAM_INTEGRATION.md`](SARVAM_AGENTSTREAM_INTEGRATION.md) | Full production guide |
| [`.env.example`](.env.example) | Copy to `.env` (gitignored) — never commit API keys |

## Prerequisites

| Item | Notes |
|------|--------|
| Python 3.10+ | venv recommended |
| Sarvam | `SARVAM_API_KEY` ([dashboard](https://www.sarvam.ai)) |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Public WSS | ngrok or cloudflared |
| Exotel env | `shared/.env.exotel` |

**Latency:** Process boot pre-synthesizes `GREETING_TEXT` so `first_audio_ms` after `start` is typically under 1 second. Generative reply TTS still takes ~1–2s (Sarvam HTTP).

## 3 steps + test call

### Step 1 — Install and configure

```bash
cd integrations/sarvam
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SARVAM_API_KEY
```

```bash
# .env
SARVAM_API_KEY=sk_...
GREETING_TEXT=Namaste! Please say something after the beep.
SAMPLE_RATE=8000
SERVER_PORT=8000
```

### Step 2 — Run the server

```bash
# From integrations/sarvam (PYTHONPATH = repo root)
export PYTHONPATH="$(cd ../.. && pwd)"
python server.py
```

On startup you should see `Greeting cache ready…`. Listen: `0.0.0.0:8000`, path `/ws`.

### Step 3 — Tunnel and place a Connect call

```bash
cloudflared tunnel --url http://127.0.0.1:8000

# From repo root
set -a && source shared/.env.exotel && set +a
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/ws?sample-rate=8000` |
| **Port** | `8000` |

### Verify

- Greeting plays quickly at normal pitch.
- Logs: `greeting cache hit`, `first_audio_ms=` under 1000, `send_pcm done`, later `user:` / `agent:` when you speak.
- Clean `stop … age_s=…` (not a ~4s silent hangup).

See [Connect Voice AI](../../docs/CONNECT_VOICE_AI.md) and [docs.exotel.com draft](../../docs/exotel-developer/sarvam.md).
