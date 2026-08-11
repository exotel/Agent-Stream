# OpenAI Realtime + AgentStream (draft)

Speech-to-speech using OpenAI Realtime (GA) over Exotel bidirectional WSS.

## Prerequisites

- OpenAI API key with Realtime
- Exotel credentials + ExoPhone
- Python 3.10+, public `wss://`

Always use `?sample-rate=8000` for PSTN. Wire format at 8 kHz is G.711 μ-law (`audio/pcmu`).

## Three steps

1. **Install** — `cd integrations/openai-realtime && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`
2. **Run** — set `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-realtime`, `SAMPLE_RATE=8000`, then `python main.py` (port **5000**)
3. **Call**:

```bash
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/?sample-rate=8000"
```

## StreamUrl

`wss://HOST/?sample-rate=8000` (path is `/`)

## Verify

Logs show `audio/pcmu → audio/pcmu` and `first_audio_ms=…`. Pitch should match a normal phone voice.

Repo README: `integrations/openai-realtime/README.md`.
