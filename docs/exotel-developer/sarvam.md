# Sarvam STT/TTS + AgentStream (draft)

Sarvam Saaras (STT) + Bulbul (TTS) echo bot on Exotel AgentStream.

## Prerequisites

- `SARVAM_API_KEY`
- Exotel credentials + ExoPhone
- Python 3.10+, public `wss://`

Greeting text is **pre-synthesized at process start** so time-to-first-audio after `start` is typically under 1 second.

## Three steps

1. **Install** — `cd integrations/sarvam && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`
2. **Run** — `export PYTHONPATH=<repo-root> && python server.py` (port **8000**)
3. **Call**:

```bash
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

## StreamUrl

`wss://HOST/ws?sample-rate=8000`

## Verify

`Greeting cache ready` at boot; on call `first_audio_ms` under 1000; speak and see `user:` / `agent:` logs.

Repo README: `integrations/sarvam/README.md`.
