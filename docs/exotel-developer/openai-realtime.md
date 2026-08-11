# OpenAI Realtime + Exotel AgentStream

Connect an Exotel phone call to [OpenAI Realtime](https://platform.openai.com/docs/guides/realtime) (speech-to-speech). Exotel stays at **8 kHz PCM**. The bridge talks to OpenAI as **PCM 16-bit at 24 kHz** and resamples both directions locally.

Sample code: [`integrations/openai-realtime`](https://github.com/exotel/Agent-Stream/tree/main/integrations/openai-realtime) in the [Agent-Stream](https://github.com/exotel/Agent-Stream) repo.

If you have not set up Connect yet, start with [Connect Voice AI with AgentStream](connect-voice-ai.md).

## What you get

- True speech-to-speech (no separate STT → LLM → TTS pipeline in your code)
- Instant pre-cached greeting on call start (optional, on by default)
- Paced AgentStream media frames suitable for Connect Voice AI

OpenAI does **not** accept linear PCM at 8 kHz. Do not set `audio/pcm` with `rate: 8000`. Use 24 kHz PCM on the OpenAI wire (this sample) or G.711 μ-law at 8 kHz if you deliberately implement that path.

## Before you start

| Item | Notes |
|------|--------|
| OpenAI | API key with Realtime access |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Python 3.10+ | On 3.13+, `audioop-lts` is pulled in via requirements |
| Public WSS | cloudflared or ngrok for the first test |

## Minute 0–5 — Install

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream

cp shared/env.exotel.example shared/.env.exotel
# Fill EXOTEL_* values

cd integrations/openai-realtime
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` (never commit this file):

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-realtime
OPENAI_VOICE=coral
SAMPLE_RATE=8000
DEFAULT_SAMPLE_RATE=8000
SERVER_PORT=5000
COMPANY_NAME=Your Company
SALES_BOT_NAME=Sara
SEND_TEST_TONE=false
INSTANT_GREETING=true
```

## Minute 5–10 — Run the bot and open a tunnel

Terminal A:

```bash
cd integrations/openai-realtime
source venv/bin/activate
python main.py
```

On startup you should see a greeting cache message, then `server listening on 0.0.0.0:5000`. WebSocket path is `/` (root).

Terminal B:

```bash
cloudflared tunnel --url http://127.0.0.1:5000
```

## Minute 10–15 — Place a Connect call

From the **repo root**:

```bash
set -a && source shared/.env.exotel && set +a

python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_CLOUDFLARE_HOST/?sample-rate=8000"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/?sample-rate=8000` |
| **Port** | `5000` |

The `?sample-rate=8000` query parameter is required for PSTN. Answer the phone: you should hear the greeting quickly, then be able to talk turn-by-turn.

## Verify

- Logs: `INSTANT greeting` (or Realtime greeting fallback), `Audio Format: audio/pcm → audio/pcm`, `first_audio_ms=…`
- Pitch sounds like a normal phone call (not stretched or deep)
- After you speak, the model replies; barge-in cancels playback when configured

## Go-live checklist

- [ ] Bot on a stable host with valid TLS for `wss://`
- [ ] `OPENAI_API_KEY` only in secrets — not in git
- [ ] `SEND_TEST_TONE=false` in production
- [ ] StreamUrl always includes `?sample-rate=8000` for 8 kHz telephony
- [ ] Voice and instructions tuned for short phone turns
- [ ] Process supervision and disconnect handling

This tree is a working sample for pilots. Large concurrent load needs multiple processes, a WSS edge, and capacity testing — it is not a multi-tenant autoscaler by itself.

## Troubleshoot

| Symptom | What to check |
|---------|----------------|
| Deep / slow voice | Old μ-law/PCM mismatch — current sample uses PCM 24 kHz ↔ 8 kHz; pull latest `core/bot.py` |
| Beep before greeting | `SEND_TEST_TONE=true` — set to `false` |
| No audio | Tunnel URL, `?sample-rate=8000`, OpenAI key / Realtime access |
| Long delay to first speech | Instant greeting cache failed (check boot logs); otherwise Realtime TTFA is often ~1–3s after connect without cache |

## Related

- Repo README: `integrations/openai-realtime/README.md`
- [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [ElevenLabs guide](elevenlabs.md) · [Sarvam guide](sarvam.md)
