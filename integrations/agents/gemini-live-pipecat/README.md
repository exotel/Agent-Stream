# Gemini Live + Pipecat on Exotel AgentStream

Gemini Live inside a Pipecat pipeline with ExotelFrameSerializer. Start from `integrations/pipecat/` and swap the LLM/STT/TTS services for Gemini Live per Pipecat docs.

## Run

```bash
cd integrations/agents/gemini-live-pipecat
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# shared package on PYTHONPATH
export PYTHONPATH="$(pwd)/../../..:$PYTHONPATH"
cp .env.example .env
python server.py
```

Default port: **8765**. WebSocket: `/ws?sample-rate=8000`

## Connect Voice AI

```bash
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).
