# Cartesia Line (S2S agent) on Exotel AgentStream

Bridge Exotel phone audio to a deployed **Cartesia Line** agent over the
[Agents WebSocket API](https://docs.cartesia.ai/line/integrations/websocket-api).

```text
Phone ←→ Exotel AgentStream ←WSS→ FastAPI /ws ←WSS→ Cartesia Line agent
```

Unlike `deepgram-gemini-cartesia-native` (Cartesia as TTS only), this recipe
talks to a full managed Line agent (`agent_…`) — STT, LLM, TTS, and turn-taking
run on Cartesia's side.

## Prerequisites

| Item | Notes |
|------|--------|
| Python 3.10–3.12 | Prefer 3.12 (`audioop` + `websockets` work cleanly) |
| Cartesia | API key (`sk_car_…`) + Line agent ID |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Public WSS | ngrok / cloudflared (Exotel must reach your `/ws`) |

## Run

```bash
cd integrations/agents/cartesia-line-native
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set CARTESIA_API_KEY + CARTESIA_AGENT_ID
python server.py
```

Default port: **4055**. WebSocket: `/ws?sample-rate=8000`

### Smoke-test Cartesia only (no phone)

```bash
python test_ws_connection.py
```

Expect `ack`, then `media_output` / transcript deltas from the agent's greeting.

## Connect Voice AI

```bash
# Terminal B — public tunnel
cloudflared tunnel --url http://127.0.0.1:4055
# or: ngrok http 4055

# Terminal C — from repo root
set -a && source shared/.env.exotel && set +a
python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/ws?sample-rate=8000` |
| **Port** | `4055` |
| **StreamType** | `bidirectional` |

See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).

## Audio

| Side | Format |
|------|--------|
| Exotel AgentStream | PCM16 LE @ 8 kHz (typical) |
| Cartesia (default) | `mulaw_8000` — PCM↔μ-law at 8 kHz, no resample |

Optional: set `CARTESIA_INPUT_FORMAT=pcm_16000` (resamples 8↔16). Match
`?sample-rate=` on the StreamUrl when using PCM formats.

`clear` from Cartesia flushes the local playback queue and sends AgentStream
`clear` (barge-in) — **ignored while the uplink gate is closed** so early
line noise cannot wipe the greeting.

### First-audio latency

Typical cold path without fixes was ~4s:

1. **~1.0–1.4s** — access-token HTTP + Cartesia WS connect/ack on every call  
2. **~2.5s** — Exotel uplink noise immediately after `ack` → false user turn
   (`"Vegas assistant."`) → Cartesia `clear` → greeting delayed until after
   that fake turn

Mitigations in this recipe:

| Fix | Env / behavior |
|-----|----------------|
| Token cache + startup `prewarm()` | First call skips token RTT |
| Uplink gate | Drop Exotel→Cartesia audio until first assistant turn ends, or `CARTESIA_UPLINK_GATE_MS` (default `2500`) |
| Ignore `clear` while gated | Protects greeting from false barge-in |
| Chunk coalesce (~40ms) | Fewer paced `send_pcm` calls for `as_available` |

Look for logs: `ready_ms=…`, `cartesia_first_media_out_ms=…`, `first_audio_ms=…`,
`uplink_open reason=…`.

## Env

| Variable | Required | Description |
|----------|----------|-------------|
| `CARTESIA_API_KEY` | yes | Server API key; exchanged for an `agent` access token |
| `CARTESIA_AGENT_ID` | yes | Line agent id (`agent_…`) |
| `CARTESIA_INPUT_FORMAT` | no | Override wire format |
| `CARTESIA_VOICE_ID` | no | Per-call voice override |
| `CARTESIA_UPLINK_GATE_MS` | no | Max ms to mute uplink (default `2500`; `0` = no gate) |
| `SERVER_PORT` | no | Default `4055` |

Auth flow matches Cartesia docs: `POST /access-token` with
`grants.agent=true`, then `Authorization: Bearer <token>` on
`wss://api.cartesia.ai/agents/stream/{agent_id}` (`Cartesia-Version: 2025-04-16`).

## Verify

- `test_ws_connection.py` prints `ack` + greeting audio/text
- Connect call: logs show `Cartesia ready … call_id=ac_…`, then `turn_started` / transcripts
- Agent speech plays at normal pitch (not slow/deep)
- Call lasts ≫ 4s
