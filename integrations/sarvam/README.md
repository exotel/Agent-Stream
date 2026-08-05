# Sarvam AI + Exotel AgentStream

Indian-language voice (Hindi, English, and 10+ languages) using **Sarvam STT/TTS** with Exotel AgentStream WSS.

| File | Purpose |
|------|---------|
| [`SARVAM_AGENTSTREAM_INTEGRATION.md`](SARVAM_AGENTSTREAM_INTEGRATION.md) | Full production guide |
| [`sarvam_agentstream_pipeline.py`](sarvam_agentstream_pipeline.py) | STT/TTS helpers (resample, Saaras, Bulbul) |

## Setup

```bash
cd integrations/sarvam
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SARVAM_API_KEY
```

Wire the helpers into your WSS bot (or OpenAI Realtime sibling) as described in the guide. The guide’s doc path in older branches was `docs/SARVAM_AGENTSTREAM_INTEGRATION.md` — canonical copy is this folder.

## Connect Voice AI test

Run any AgentStream-compatible bot that uses these helpers, then:

```bash
python ../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../docs/CONNECT_VOICE_AI.md).
