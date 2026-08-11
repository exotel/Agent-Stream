# Cartesia Line + Exotel AgentStream

Connect an Exotel phone call to a deployed [Cartesia Line](https://docs.cartesia.ai/line/introduction) voice agent over AgentStream. Cartesia runs the full speech-to-speech stack (STT, LLM, TTS, turn-taking). Your bridge only moves PCM between Exotel and Cartesia’s [Agents WebSocket API](https://docs.cartesia.ai/line/integrations/websocket-api).

Sample code: [`integrations/agents/cartesia-line-native`](https://github.com/exotel/Agent-Stream/tree/main/integrations/agents/cartesia-line-native) in the [Agent-Stream](https://github.com/exotel/Agent-Stream) repo.

If you have not set up Connect yet, start with [Connect Voice AI with AgentStream](connect-voice-ai.md).

## What you get

- Outbound (or inbound via applet) calls that talk to your Cartesia Line agent (`agent_…`)
- Bidirectional AgentStream PCM at 8 kHz (telephony default)
- Uplink gate so early line noise does not barge into the greeting
- Access-token cache + startup prewarm to cut first-media latency

```text
Caller  ←→  Exotel  ←WSS PCM→  FastAPI /ws  ←WSS→  Cartesia Line agent
```

This is **not** the same as using Cartesia Sonic as TTS inside a cascaded STT→LLM→TTS pipeline (for example Pipecat or `deepgram-gemini-cartesia-native`). Here the Line agent owns the conversation.

## Before you start

| Item | Notes |
|------|--------|
| Cartesia | API key (`sk_car_…`) + deployed Line agent ID (`agent_…`) |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Python 3.10–3.12 | Prefer 3.12 (`audioop` + `websockets` work cleanly) |
| Public WSS | cloudflared or ngrok for the first test |

**Audio tip:** Default wire format is Cartesia `mulaw_8000` (μ-law at 8 kHz). Exotel AgentStream stays PCM16 @ 8 kHz; the bridge converts both ways with no resample. That keeps pitch/speed correct on the handset.

## Minute 0–5 — Install

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream

cp shared/env.exotel.example shared/.env.exotel
# Fill EXOTEL_ACCOUNT_SID, EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_CALLER_ID

cd integrations/agents/cartesia-line-native
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` (never commit this file):

```bash
CARTESIA_API_KEY=sk_car_...
CARTESIA_AGENT_ID=agent_...
SERVER_PORT=4055
# Optional: CARTESIA_UPLINK_GATE_MS=2500
```

Smoke-test Cartesia alone (no phone):

```bash
python test_ws_connection.py
```

You should see `ack`, then `media_output` / transcript deltas from the agent greeting.

## Minute 5–10 — Run the bridge and open a tunnel

Terminal A:

```bash
cd integrations/agents/cartesia-line-native
source venv/bin/activate
python server.py
```

On startup you should see `Cartesia access token prewarmed`, then Uvicorn on `0.0.0.0:4055`. WebSocket path: `/ws`.

Terminal B:

```bash
cloudflared tunnel --url http://127.0.0.1:4055
# or: ngrok http 4055
```

## Minute 10–15 — Place a Connect call

From the **repo root**:

```bash
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

Answer the handset. The Line agent should greet within about **1–1.5s** of AgentStream `start` (after token prewarm), then respond when you speak.

## Auth (Cartesia)

Server-side flow matches Cartesia docs:

1. `POST https://api.cartesia.ai/access-token` with `grants: { "agent": true }`
2. Connect `wss://api.cartesia.ai/agents/stream/{agent_id}` with  
   `Authorization: Bearer <token>` and `Cartesia-Version: 2025-04-16`
3. First message must be `start` (`input_format`, optional `voice_id` / agent overrides)
4. Stream `media_input` / receive `media_output`, handle `clear`, conversation events

This sample caches the token and refreshes it before expiry so later calls skip the HTTP RTT.

## Latency notes

Without gating, first audio can land around **4s** because:

1. Cold access-token + WebSocket connect (~1s)
2. Early Exotel uplink noise is treated as a user turn → Cartesia `clear` delays the greeting (~2–3s)

The sample mitigates both (token prewarm + uplink gate). Useful log lines:

- `ready_ms=…` / `token_ms=…` / `ws_ms=…` / `ack_ms=…`
- `cartesia_first_media_out_ms=…` / `since_ack_ms=…`
- `first_audio_ms=…`
- `uplink_open reason=assistant_turn_ended|gate_timeout`

Tune `CARTESIA_UPLINK_GATE_MS` (default `2500`). Set `0` to disable the gate.

## Verify

- `test_ws_connection.py` prints `ack` + greeting audio/text
- Connect call logs show `Cartesia ready … call_id=ac_…` then `turn_started … role=assistant`
- Voice is normal pitch/speed (not slow/deep)
- Call lasts well beyond a few seconds

## Go-live checklist

- [ ] Bridge on a stable host with real TLS for `wss://`
- [ ] API keys only in env / secret store
- [ ] `CARTESIA_AGENT_ID` points at the production Line deployment
- [ ] Uplink gate tuned for your greeting length
- [ ] Monitoring on process health, Cartesia disconnect reasons, `first_audio_ms`
- [ ] Load-tested concurrent calls for expected traffic

## Troubleshoot

| Symptom | What to check |
|---------|----------------|
| Call drops in ~4 seconds | StreamUrl path / `?sample-rate=8000`; tunnel; bot accepting WSS |
| Slow / deep voice | Confirm Exotel is 8 kHz and Cartesia format is `mulaw_8000` (or matching PCM rate) |
| Greeting delayed / cut off | Uplink gate (`CARTESIA_UPLINK_GATE_MS`); look for false `turn_started role=user` before assistant |
| No agent audio | API key, agent ID, `access-token` with `agent` grant, Cartesia console / call record |
| `ack` timeout | Agent deployment status; `Cartesia-Version` header; network to `api.cartesia.ai` |

## Related

- Recipe README: `integrations/agents/cartesia-line-native/README.md`
- [Cartesia Agents WebSocket API](https://docs.cartesia.ai/line/integrations/websocket-api)
- [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [ElevenLabs](elevenlabs.md) · [OpenAI Realtime](openai-realtime.md) · [Pipecat](pipecat.md)
