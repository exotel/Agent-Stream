# ElevenLabs Conversational AI + AgentStream (draft)

Connect Exotel phone calls to an ElevenLabs ConvAI agent via AgentStream.

## Prerequisites

- ElevenLabs agent ID + API key
- Exotel Account SID, API Key, API Token, ExoPhone
- Python 3.10+, public `wss://` (ngrok / cloudflared)

Prefer agent audio format **pcm_8000** to avoid 16→8 kHz resample artifacts.

## Three steps

1. **Install** — `cd integrations/elevenlabs && python3 -m venv venv && source venv/bin/activate && pip install -r exotel/requirements.txt`
2. **Run** — `python exotel/bridge.py --port 10002 --agent-id $ELEVENLABS_AGENT_ID --api-key $ELEVENLABS_API_KEY`
3. **Call** — tunnel port 10002, then:

```bash
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/v1/convai/conversation/exotel"
```

## StreamUrl

`wss://HOST/v1/convai/conversation/exotel`

## Verify

Agent speaks at normal pitch; bridge logs `first_audio_ms=…`. See repo README: `integrations/elevenlabs/README.md`.
