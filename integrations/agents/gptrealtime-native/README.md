# GPT Realtime (S2S) on Exotel AgentStream

Speech-to-speech with OpenAI Realtime. Prefer the production package at `integrations/openai-realtime/` for the full bot; this recipe documents the Connect Voice AI wiring and points at that implementation.

## Run

```bash
cd integrations/agents/gptrealtime-native
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# shared package on PYTHONPATH
export PYTHONPATH="$(pwd)/../../..:$PYTHONPATH"
cp .env.example .env
python server.py
```

Default port: **5000**. WebSocket: `/ws?sample-rate=8000`

## Connect Voice AI

```bash
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).
