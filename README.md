# Agent-Stream — Exotel Voice AI integrations

Sample and production-oriented bridges that connect **Exotel AgentStream** (bidirectional WebSocket audio) to Voice AI providers. Place outbound calls with the [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api).

## Choose a provider

| Provider | Path | Language | Best for |
|----------|------|----------|----------|
| **OpenAI Realtime** | [`integrations/openai-realtime`](integrations/openai-realtime/) | Python | Speech-to-speech realtime |
| **ElevenLabs** | [`integrations/elevenlabs`](integrations/elevenlabs/) | Python | Conversational AI + ambience |
| **Gemini Live** | [`integrations/gemini-live`](integrations/gemini-live/) | Node.js | Google Gemini Live |
| **Sarvam** | [`integrations/sarvam`](integrations/sarvam/) | Python | Indian languages (STT/TTS) |
| **Pipecat** | [`integrations/pipecat`](integrations/pipecat/) | Python | Pluggable STT → LLM → TTS ([ExotelFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel)) |
| **Dograh** | [`integrations/dograh`](integrations/dograh/) | Python | Drop Exotel telephony into [Dograh](https://github.com/dograh-hq/dograh) (platform wiring, not an AI vendor) |

## Quick start (OpenAI — still works from repo root)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp env.example .env   # set OPENAI_API_KEY
python main.py        # shim → integrations/openai-realtime
```

Canonical OpenAI package: `integrations/openai-realtime/`.

## Test with Connect Voice AI

1. Start a bridge and expose it (`ngrok http <port>` → `wss://…`).
2. Configure Exotel credentials (`shared/env.exotel.example`).
3. Place a call:

```bash
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/?sample-rate=8000"
```

Details: [`docs/CONNECT_VOICE_AI.md`](docs/CONNECT_VOICE_AI.md) · WSS protocol: [`docs/AGENTSTREAM_WSS_PROTOCOL.md`](docs/AGENTSTREAM_WSS_PROTOCOL.md)

## Layout

```text
shared/                 # place_connect_call.py + Exotel env example
docs/                   # Connect API + WSS protocol
integrations/<provider>/  # self-contained bridge + README + deps
```

## Prerequisites

- Python 3.8+ (and Node 18+ for Gemini Live)
- Exotel account with Voicebot / Connect Voice AI enabled
- Provider API keys for the integration you run

## License

MIT — see [LICENSE](LICENSE).
