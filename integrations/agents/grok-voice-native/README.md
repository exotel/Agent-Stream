# Grok Voice (speech-to-speech) on Exotel AgentStream

Real-time **speech-to-speech** bridge: Exotel AgentStream PCM ↔ xAI **Grok Voice** Realtime WebSocket (`wss://api.x.ai/v1/realtime`).

This is not an STT→LLM→TTS pipeline. Grok handles turn-taking (server VAD), barge-in, and audio out on one connection. Latency / quality figures are **not yet benchmarked**.

## Architecture

```text
Caller
  ↕ PSTN
Exotel AgentStream (PCM16, bidirectional WSS)
  ↕ /ws?sample-rate=8000|16000|24000
This bot (FastAPI)
  ↕ wss://api.x.ai/v1/realtime?model=grok-voice-latest
Grok Voice (S2S)
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `XAI_API_KEY` | Yes | xAI API key (Bearer auth on the realtime WS) |
| `GROK_MODEL` | No | Default `grok-voice-latest` |
| `GROK_VOICE` | No | Built-in voice id, lowercase (default `eve`) |
| `GROK_SILENCE_MS` | No | Server VAD silence window (default `600`) |
| `GREETING_TEXT` | No | Spoken via `force_message` on connect |
| `SYSTEM_PROMPT` | No | Session instructions |
| `SERVER_PORT` | No | Default `8000` |
| `EXOTEL_*` | For Connect test | See Connect Voice AI below |

## Quick start

```bash
cd integrations/agents/grok-voice-native
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$(pwd)/../../..:$PYTHONPATH"
cp .env.example .env   # set XAI_API_KEY
python server.py
```

- Listen: `0.0.0.0:8000`
- Health: `GET /health`
- AgentStream path: `/ws?sample-rate=8000`

## Audio notes (Grok Voice)

| Direction | Format | Sample rate |
|-----------|--------|-------------|
| Exotel ↔ bot | PCM16 LE mono (AgentStream) | `8000` / `16000` / `24000` via query |
| Bot ↔ Grok | `audio/pcm` (PCM16 LE) over JSON base64 deltas | Matched to the Exotel stream rate |

Grok also supports `audio/pcmu` / `audio/pcma` at 8 kHz; this recipe stays on PCM16 to match AgentStream media events. Prefer `?sample-rate=8000` for PSTN unless you have upgraded AgentStream rates enabled.

## Connect Voice AI test

```bash
# Terminal A: python server.py
# Terminal B: ngrok http 8000   → note the https host, use wss://

python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_NGROK_HOST/ws?sample-rate=8000"
```

Load Exotel credentials from `shared/env.exotel.example` → `.env.exotel` (or export `EXOTEL_ACCOUNT_SID`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_CALLER_ID`). Details: [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).

## Troubleshooting

| Symptom | Likely cause | What to check |
|---------|--------------|---------------|
| Session starts but no greeting / no speech | Missing or invalid `XAI_API_KEY`, or model id rejected | Bot logs for `Grok Voice error`; confirm `GROK_MODEL=grok-voice-latest` |
| One-way audio (caller hears nothing) | Sample-rate mismatch or ngrok HTTP instead of WSS path | Use `wss://…/ws?sample-rate=8000` (not root `/`); confirm `/health` on the tunnel |
| Bot talks over the caller | Barge-in clear not firing or VAD too slow | Look for `speech_started` handling; raise/lower `GROK_SILENCE_MS` |
| Connect API 4xx | Bad Exotel Basic auth or CallerId | Account SID + API key/token + ExoPhone in E.164 |

## References

| Resource | URL |
|----------|-----|
| Grok Voice Agent (Realtime) | https://docs.x.ai/developers/model-capabilities/audio/voice-agent |
| xAI Voice overview | https://docs.x.ai/developers/model-capabilities/audio/voice |
| Exotel Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS protocol | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
