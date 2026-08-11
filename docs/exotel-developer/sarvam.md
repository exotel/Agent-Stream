# Sarvam AI + Exotel AgentStream

Run an Indian-language voice bot on Exotel using [Sarvam](https://www.sarvam.ai) **Saaras** (STT) and **Bulbul** (TTS). This is a cascaded pipeline (speech → text → speech), not native speech-to-speech.

Sample code: [`integrations/sarvam`](https://github.com/exotel/Agent-Stream/tree/main/integrations/sarvam) in the [Agent-Stream](https://github.com/exotel/Agent-Stream) repo.

If you have not set up Connect yet, start with [Connect Voice AI with AgentStream](connect-voice-ai.md).

## What you get

- AgentStream WebSocket server (`server.py`) that greets the caller and echoes turns via Sarvam
- Greeting audio **pre-synthesized at process start** so time-to-first-audio after `start` is usually under one second
- Paced PCM frames aligned with AgentStream expectations (~100 ms)

For a deeper production write-up, see `integrations/sarvam/SARVAM_AGENTSTREAM_INTEGRATION.md` in the repo.

## Before you start

| Item | Notes |
|------|--------|
| Sarvam | `SARVAM_API_KEY` from the Sarvam dashboard |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Python 3.10+ | Virtualenv recommended |
| Public WSS | cloudflared or ngrok for the first test |

## Minute 0–5 — Install

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream

cp shared/env.exotel.example shared/.env.exotel
# Fill EXOTEL_* values

cd integrations/sarvam
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```bash
SARVAM_API_KEY=sk_...
GREETING_TEXT=Namaste! Please say something after the beep.
SAMPLE_RATE=8000
SERVER_PORT=8000
```

## Minute 5–10 — Run the server and open a tunnel

Terminal A (from `integrations/sarvam`):

```bash
source venv/bin/activate
export PYTHONPATH="$(cd ../.. && pwd)"
python server.py
```

You should see `Greeting cache ready…` and a listener on `0.0.0.0:8000`. WebSocket path: `/ws`.

Terminal B:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
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
| **Port** | `8000` |

Answer the phone. The greeting should play quickly. Speak a short sentence; watch `user:` / `agent:` style logs and hear the reply.

## Verify

- Boot: `Greeting cache ready`
- Call: `first_audio_ms` typically under 1000 for the cached greeting
- After you speak: STT text and TTS playback; clean `stop` when the call ends

Note: generative replies still wait on Sarvam HTTP TTS (~1–2 seconds). Only the greeting is pre-warmed.

## Go-live checklist

- [ ] Server on a stable host with valid TLS for `wss://`
- [ ] `SARVAM_API_KEY` only in secrets
- [ ] StreamUrl includes `/ws?sample-rate=8000`
- [ ] Greeting text and language settings match your market
- [ ] Timeouts and concurrency limits sized for Sarvam API quotas
- [ ] Consider caching common prompts if you need lower reply latency

## Troubleshoot

| Symptom | What to check |
|---------|----------------|
| No greeting | Boot cache failed — check API key and `GREETING_TEXT`; look for cache errors |
| Hangup in a few seconds | Wrong StreamUrl (must include `/ws`); tunnel down |
| Slow replies after you speak | Expected for HTTP STT/TTS; shorten prompts or cache TTS |
| Wrong language | Sarvam language / speaker settings in pipeline config |

## Related

- Repo README: `integrations/sarvam/README.md`
- Full guide: `integrations/sarvam/SARVAM_AGENTSTREAM_INTEGRATION.md`
- [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [ElevenLabs guide](elevenlabs.md) · [OpenAI Realtime guide](openai-realtime.md)
