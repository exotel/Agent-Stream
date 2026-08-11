# Connect Voice AI API

Programmatically place a call and stream bidirectional audio to your bot’s WebSocket.

**Docs:** [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)

## Flow

1. Start an integration bridge (see [integrations/](../integrations/)).
2. Expose it publicly (`wss://…`, e.g. ngrok).
3. Call Connect with `StreamType=bidirectional` and your `StreamUrl`.

```text
Caller ←→ Exotel ←WSS PCM→ your bot (OpenAI / ElevenLabs / Gemini / Sarvam / Pipecat / …)
```

## Auth

HTTP Basic: **API Key** as username, **API Token** as password.

## Endpoint

| Region | Base URL |
|--------|----------|
| Mumbai | `https://api.in.exotel.com` |
| Singapore | `https://api.exotel.com` |

```http
POST /v1/Accounts/{AccountSid}/Calls/connect
```

### Required

| Field | Description |
|-------|-------------|
| `From` | Number to dial (E.164, e.g. `+919876543210`) |
| `CallerId` | Your ExoPhone |
| `StreamUrl` | Bot WSS (`ws://` or `wss://`), under 600 chars |
| `StreamType` | Must be `bidirectional` |

### Optional

`Record`, `RecordingChannels`, `TimeLimit`, `CustomField`, `StatusCallback`, `StatusCallbackEvents[]`, `StreamName`

## Sample rate

Append to `StreamUrl`:

```text
wss://your-bot.example.com/media?sample-rate=16000
```

Supported: `8000`, `16000`, `24000`. Default is often 8 kHz PCM16 (linear, not μ-law).

## Curl

```bash
curl -X POST \
  "https://$EXOTEL_API_KEY:$EXOTEL_API_TOKEN@api.in.exotel.com/v1/Accounts/$EXOTEL_ACCOUNT_SID/Calls/connect" \
  -F 'StreamType=bidirectional' \
  -F "StreamUrl=wss://your-bot.example.com/?sample-rate=8000" \
  -F "From=+91XXXXXXXXXX" \
  -F "CallerId=0XXXXXXXXXX" \
  -F 'Record=false'
```

## Repo helper

```bash
cp shared/env.exotel.example .env.exotel   # fill in values
set -a && source .env.exotel && set +a

# Point StreamUrl at whichever integration you started
# ElevenLabs:  wss://HOST/v1/convai/conversation/exotel
# OpenAI:      wss://HOST/?sample-rate=8000
# Sarvam:      wss://HOST/ws?sample-rate=8000
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_PUBLIC_HOST/?sample-rate=8000"
```

Provider 3-step guides: [ElevenLabs](../integrations/elevenlabs/README.md), [OpenAI Realtime](../integrations/openai-realtime/README.md), [Sarvam](../integrations/sarvam/README.md). Drafts for docs.exotel.com: [docs/exotel-developer/](exotel-developer/).

## Notes

- Feature must be enabled on the account (contact Exotel if needed).
- When the bot closes the WebSocket, the call ends.
- Use `StatusCallback` for answered / terminal events.
