# Connect Voice AI with AgentStream

Use Exotel [AgentStream](https://docs.exotel.com/exotel-agentstream) to stream live call audio to your bot over WebSocket, and play bot audio back to the caller.

This page gets you from zero to a working outbound test call. Pick one provider guide when you are ready to wire a full voice agent.

**API reference:** [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)

## How it works

```text
Caller  ←→  Exotel  ←WSS PCM→  your bot (public wss://)
```

1. You run a bot that speaks the AgentStream events: `connected`, `start`, `media`, `stop` (and optionally `mark` / `clear`).
2. You expose that bot as a public `wss://` URL (TLS).
3. You place a call with Connect Voice AI (`StreamType=bidirectional`, `StreamUrl` = your bot).

Telephony default on AgentStream is **8 kHz, 16-bit PCM, mono**. Always pass the sample rate your bot expects on the StreamUrl query string when the bot documents it (usually `?sample-rate=8000`).

## Before you start

| You need | Notes |
|----------|--------|
| Exotel account | Account SID, API Key, API Token, ExoPhone (CallerId) |
| A phone number to call | E.164, for example `+91…` |
| Public WSS | cloudflared, ngrok, or your own HTTPS load balancer |
| Python 3.10+ | For the sample bots and `place_connect_call.py` |

Clone the sample repo:

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream
cp shared/env.exotel.example shared/.env.exotel
# Edit shared/.env.exotel with EXOTEL_ACCOUNT_SID, EXOTEL_API_KEY,
# EXOTEL_API_TOKEN, EXOTEL_CALLER_ID
```

## Pick a provider (about 15 minutes each)

| Guide | Mode | Default port | StreamUrl |
|-------|------|--------------|-----------|
| [ElevenLabs](elevenlabs.md) | Speech-to-speech (ConvAI) | 10002 | `wss://HOST/v1/convai/conversation/exotel` |
| [OpenAI Realtime](openai-realtime.md) | Speech-to-speech (Realtime GA) | 5000 | `wss://HOST/?sample-rate=8000` |
| [Sarvam](sarvam.md) | STT → TTS (Saaras / Bulbul) | 8000 | `wss://HOST/ws?sample-rate=8000` |

Replace `HOST` with your tunnel hostname (no `https://` prefix on StreamUrl — use `wss://`).

## Place a Connect call (shared helper)

From the repo root, after your bot and tunnel are up:

```bash
set -a && source shared/.env.exotel && set +a

python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/…see table above…"
```

Endpoint used by the helper:

`POST /v1/Accounts/{AccountSid}/Calls/connect`  
Auth: HTTP Basic (API Key / API Token)

| Field | Required | Description |
|-------|----------|-------------|
| `From` | yes | Callee in E.164 |
| `CallerId` | yes | Your ExoPhone |
| `StreamUrl` | yes | Bot WSS URL (keep under ~600 characters) |
| `StreamType` | yes | `bidirectional` |

## Go-live checklist (any provider)

- Bot listens on a stable host with a valid TLS certificate (not a disposable laptop tunnel for production).
- Secrets live in environment variables or a secret store — never in git.
- StreamUrl path and `sample-rate` match the provider README exactly.
- You verified pitch (not slow/deep) and at least one full user turn on a real handset.
- You read [AgentStream WSS errors and handling](https://docs.exotel.com/exotel-agentstream) for disconnect and timeout behaviour.

## Next

- [ElevenLabs Conversational AI](elevenlabs.md)
- [OpenAI Realtime](openai-realtime.md)
- [Sarvam STT/TTS](sarvam.md)
