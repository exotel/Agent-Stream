# OpenAI Realtime + Exotel AgentStream

Speech-to-speech bot using **OpenAI Realtime API** over Exotel bidirectional WSS.

This is the canonical location for the sample that previously lived at the repo root.  
**Root compatibility:** `python main.py` from the repository root still works (shim).

## Setup

```bash
cd integrations/openai-realtime
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY
python main.py
```

Default listen: `0.0.0.0:5000`.

## Connect Voice AI test

```bash
# Public WSS (ngrok http 5000 → wss://….ngrok-free.app/?sample-rate=8000)
python ../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../docs/CONNECT_VOICE_AI.md).
