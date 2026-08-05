# Deepgram + GPT + Grok TTS (native pipeline)

STT Deepgram → LLM GPT → TTS xAI Grok on Exotel AgentStream.

## Run

```bash
cd integrations/agents/deepgram-gpt-groktts-native
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# shared package on PYTHONPATH
export PYTHONPATH="$(pwd)/../../..:$PYTHONPATH"
cp .env.example .env
python server.py
```

Default port: **8000**. WebSocket: `/ws?sample-rate=8000`

## Connect Voice AI

```bash
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).
