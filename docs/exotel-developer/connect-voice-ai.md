# Connect Voice AI API (draft)

Place an outbound call and stream bidirectional PCM to your bot WebSocket.

**Published:** [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)

## Flow

1. Start a bot that speaks AgentStream (`connected` / `start` / `media` / `stop`).
2. Expose it as public `wss://…`.
3. Call Connect with `StreamType=bidirectional` and `StreamUrl`.

```text
Caller ←→ Exotel ←WSS PCM→ your bot
```

## Endpoint

`POST /v1/Accounts/{AccountSid}/Calls/connect`  
Auth: HTTP Basic (API Key / API Token)

| Field | Required | Description |
|-------|----------|-------------|
| `From` | yes | Callee E.164 |
| `CallerId` | yes | ExoPhone |
| `StreamUrl` | yes | Bot WSS (&lt; 600 chars) |
| `StreamType` | yes | `bidirectional` |

Sample rate: append `?sample-rate=8000` (also `16000`, `24000`). Default telephony is often **8 kHz PCM16**.

## Quick test (Agent-Stream repo)

```bash
cp shared/env.exotel.example shared/.env.exotel   # fill values
set -a && source shared/.env.exotel && set +a

python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

## Provider quickstarts

- [ElevenLabs](elevenlabs.md) — `wss://HOST/v1/convai/conversation/exotel`
- [OpenAI Realtime](openai-realtime.md) — `wss://HOST/?sample-rate=8000`
- [Sarvam](sarvam.md) — `wss://HOST/ws?sample-rate=8000`
