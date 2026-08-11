# Pipecat + Exotel AgentStream

Pluggable **STT → LLM → TTS** voice bot over Exotel WebSocket media using Pipecat’s [`ExotelFrameSerializer`](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel).

Default pipeline: **Deepgram STT** → **OpenAI LLM** → **Cartesia TTS** (swap services in `bot.py` as needed).

**Docs portal article:** [Build a modular voice agent with Pipecat on Exotel AgentStream](../../docs/exotel-developer/pipecat.md)

## Exotel / Pipecat notes

From the [serializer docs](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel) and [Exotel WebSocket guide](https://docs.pipecat.ai/pipecat/telephony/exotel-websockets):

- Audio is **16-bit linear PCM** (not μ-law), typically **8 kHz**
- Serializer does **not** auto hang-up — close the WebSocket to end the call
- DTMF becomes `InputDTMFFrame`
- Official examples: [pipecat-examples/exotel-chatbot](https://github.com/pipecat-ai/pipecat-examples/tree/main/exotel-chatbot)

## Setup

```bash
cd integrations/pipecat
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # OPENAI / DEEPGRAM / CARTESIA (+ Exotel for Connect)
python server.py
```

Listens on `0.0.0.0:8765` by default. WebSocket path: `/ws`

Voicebot applet / Connect `StreamUrl` example:

```text
wss://YOUR_HOST/ws?sample-rate=8000
```

## Connect Voice AI test

```bash
# Terminal 1: python server.py  (+ cloudflared tunnel --url http://127.0.0.1:8765)
python ../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

See [docs/exotel-developer/pipecat.md](../../docs/exotel-developer/pipecat.md) and [Connect Voice AI](../../docs/exotel-developer/connect-voice-ai.md).

## Files

| File | Role |
|------|------|
| `server.py` | FastAPI WSS host + ExotelFrameSerializer transport |
| `bot.py` | Pipeline (STT / LLM / TTS), VAD + Smart Turn |
| `greeting_cache.py` | Boot-time Cartesia greeting (same voice as live TTS) |
| `voice_config.py` | Shared voice / rate / encoding |
| `ATTRIBUTION.md` | Upstream Pipecat examples credit |
