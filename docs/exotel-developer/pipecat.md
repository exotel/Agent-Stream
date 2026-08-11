# Build a modular voice agent with Pipecat on Exotel AgentStream

Wire Exotel phone audio to a **Pipecat** pipeline using the official [`ExotelFrameSerializer`](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel). Default stack: **Deepgram STT → OpenAI LLM → Cartesia TTS** at **8 kHz PCM**. Swap any stage in `bot.py` without rewriting the Exotel WebSocket glue.

Sample code: [`integrations/pipecat`](https://github.com/exotel/Agent-Stream/tree/main/integrations/pipecat) in the [Agent-Stream](https://github.com/exotel/Agent-Stream) repo.

If you have not set up Connect yet, start with [Connect Voice AI with AgentStream](connect-voice-ai.md).

## When to use Pipecat (vs speech-to-speech)

| | Pipecat cascade | OpenAI Realtime / ElevenLabs |
|--|-----------------|-------------------------------|
| Shape | STT → LLM → TTS (you own each hop) | Native speech-to-speech |
| Best for | Swappable vendors, custom tools, cost control per stage | Lowest conversational latency and barge-in feel |
| Expect | ~turn detection + LLM + TTS before reply audio | Model speaks as it “thinks” |

Use this guide when you want a **composable** AgentStream bot. For the most natural phone talk, prefer the [OpenAI Realtime](openai-realtime.md) or [ElevenLabs](elevenlabs.md) guides.

## What you get

- FastAPI WebSocket host that speaks Exotel AgentStream (`/ws`)
- Pipecat `ExotelFrameSerializer` (16-bit linear PCM, typically 8 kHz — not μ-law)
- Boot-time **Cartesia greeting cache** (same voice ID as live TTS) for near-instant first media
- Tuned turn-taking: Silero VAD + Local Smart Turn (sub-second silence stop)
- Official Pipecat Exotel notes: [Exotel WebSockets](https://docs.pipecat.ai/pipecat/telephony/exotel-websockets)

## Before you start

| Item | Notes |
|------|--------|
| OpenAI | `OPENAI_API_KEY` (LLM replies) |
| Deepgram | `DEEPGRAM_API_KEY` (STT) |
| Cartesia | `CARTESIA_API_KEY` (+ optional `CARTESIA_VOICE_ID`) |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Python 3.10+ | Virtualenv recommended |
| Public WSS | cloudflared or ngrok for the first test |

## Minute 0–5 — Install

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream

cp shared/env.exotel.example shared/.env.exotel
# Fill EXOTEL_* values

cd integrations/pipecat
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` (never commit this file):

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=sk_car_...
CARTESIA_VOICE_ID=71a7ad14-091c-4e8e-a314-022ece01c121
CARTESIA_MODEL=sonic-3.5
PIPECAT_GREETING=Hi, how can I help?
SMART_TURN_STOP_SECS=0.8
SERVER_HOST=0.0.0.0
SERVER_PORT=8765
```

Keep `CARTESIA_VOICE_ID` / `CARTESIA_MODEL` / 8 kHz PCM the same for the greeting cache and live TTS so the agent voice stays consistent.

## Minute 5–10 — Run the bot and open a tunnel

Terminal A:

```bash
cd integrations/pipecat
source venv/bin/activate
python server.py
```

On startup you should see:

- `Cartesia TTS websocket warmed`
- `Greeting cache ready …`
- `Pipecat Exotel bridge ready — WSS /ws`
- Uvicorn on `0.0.0.0:8765`

WebSocket path: `/ws`.

Terminal B:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

## Minute 10–15 — Place a Connect call

From the **repo root**:

```bash
set -a && source shared/.env.exotel && set +a

python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_CLOUDFLARE_HOST/ws?sample-rate=8000"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/ws?sample-rate=8000` |
| **Port** | `8765` |

The `?sample-rate=8000` query parameter is required for PSTN. Answer the phone: you should hear the cached greeting quickly, then speak a short turn and get an LLM + Cartesia reply.

## Architecture (what runs on each call)

```text
Caller ←→ Exotel AgentStream (8 kHz PCM)
              ↕ wss://…/ws
         FastAPI + ExotelFrameSerializer
              ↕
         Pipecat pipeline
           Deepgram STT → user aggregator (VAD + Smart Turn)
             → OpenAI LLM → Cartesia TTS → Exotel media out
```

| Piece | Role |
|-------|------|
| `server.py` | Accept Exotel WSS, build transport + serializer, run one bot session |
| `bot.py` | Pipeline, VAD / Smart Turn, LLM, Cartesia TTS |
| `greeting_cache.py` | Boot synthesize + silence trim; push PCM on connect |
| `voice_config.py` | Shared voice / rate / encoding for cache and live TTS |

Pipecat does **not** auto hang-up via Exotel REST in this sample — ending the WebSocket ends the media bridge. See the [serializer docs](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel).

## Verify

- Boot: `Greeting cache ready` and `voice=<same CARTESIA_VOICE_ID>`
- Connect: `cached greeting … queue_ms≈0`
- After you speak: Smart Turn completes in under ~1s of silence (not ~3s)
- Reply audio sounds natural (sentence-level Cartesia), not stretched word-by-word
- Pitch matches a normal phone call (8 kHz end-to-end, no μ-law mix-up)

## Latency expectations (honest)

| Stage | Typical | Notes |
|-------|---------|--------|
| First greeting | Near 0 ms after pipeline ready | Pre-cached Cartesia PCM |
| End-of-user-turn | ~0.8s silence (configurable) | `SMART_TURN_STOP_SECS` (Pipecat default is 3.0 — too slow for phones) |
| LLM TTFB | ~0.5–2s | Use `gpt-4o-mini` (or similar) for voice |
| Cartesia TTFA | ~0.2s | Plus small leading silence from the model |

This is still a **cascade**. Speech-to-speech providers will feel snappier for free-form chat.

## Go-live checklist

- [ ] Bot on a stable host with valid TLS for `wss://`
- [ ] API keys only in secrets — not in git
- [ ] StreamUrl is `wss://HOST/ws?sample-rate=8000`
- [ ] Greeting text / voice ID match your brand
- [ ] `SMART_TURN_STOP_SECS` tuned on real handsets (too low cuts users off mid-thought)
- [ ] Cartesia uses **sentence** aggregation for natural speech (do not force token flush with `max_buffer_delay_ms=0` unless you accept choppy audio)
- [ ] Process supervision and clean disconnect handling
- [ ] Capacity test: one process ≠ unlimited concurrent calls

## Troubleshoot

| Symptom | What to check |
|---------|----------------|
| No greeting | Boot cache failed — `CARTESIA_API_KEY`, network; look for `Greeting warm failed` |
| Silence after connect | Tunnel URL, path `/ws`, `?sample-rate=8000` |
| ~3s dead air before every reply | Smart Turn still at default 3s — set `SMART_TURN_STOP_SECS=0.8` |
| “Hello……how……can……” stretched speech | Token-level TTS flush — use sentence aggregation (sample default) |
| Deep / slow voice | Sample-rate mismatch — keep pipeline and Cartesia at 8000 PCM |
| Hangup in a few seconds | Wrong StreamUrl or tunnel died |
| Slow LLM | Switch `OPENAI_MODEL` to a low-latency chat model; shorten system prompt |

## Swap STT / LLM / TTS

Edit `integrations/pipecat/bot.py`. Keep:

- `audio_in_sample_rate` / `audio_out_sample_rate` = `8000`
- Transport + `ExotelFrameSerializer` unchanged in `server.py`
- Greeting cache voice settings in sync if you change Cartesia (or re-point cache at your new TTS)

Upstream patterns: [pipecat-examples/exotel-chatbot](https://github.com/pipecat-ai/pipecat-examples/tree/main/exotel-chatbot).

## Related

- Repo README: `integrations/pipecat/README.md`
- [Pipecat ExotelFrameSerializer](https://docs.pipecat.ai/api-reference/server/services/serializers/exotel)
- [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [OpenAI Realtime](openai-realtime.md) · [ElevenLabs](elevenlabs.md) · [Sarvam](sarvam.md)
