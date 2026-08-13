# Deepgram + Gemini + Cartesia (native pipeline)

Turn-based phone agent on Exotel AgentStream:

**Deepgram Nova (STT) → Google Gemini (LLM) → Cartesia Sonic (TTS)**

Uses the shared silence-gated pipeline (`PipelineSession`). Not a full production VAD stack — tune `VAD_RMS_THRESHOLD` / silence windows for your traffic. End-to-end latency is **not yet benchmarked**.

## Architecture

```text
Caller ↔ Exotel AgentStream (PCM16 WSS)
         ↕ /ws?sample-rate=8000
This bot
  → Deepgram /v1/listen (WAV @ 16 kHz)
  → Gemini generateContent
  → Cartesia /tts/bytes (raw pcm_s16le @ call rate)
  → Exotel media frames
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `DEEPGRAM_API_KEY` | Yes | Deepgram listen API |
| `GOOGLE_API_KEY` | Yes | Gemini Developer API key |
| `GEMINI_MODEL` | No | Default `gemini-2.0-flash` |
| `CARTESIA_API_KEY` | Yes | Cartesia TTS |
| `CARTESIA_VOICE_ID` | No | Voice UUID (recipe has a default) |
| `CARTESIA_MODEL` | No | Default `sonic-english` |
| `SERVER_PORT` | No | Default `8000` |
| `SYSTEM_PROMPT` / `GREETING_TEXT` | No | LLM system prompt / opening TTS line |

## Quick start

```bash
cd integrations/agents/deepgram-gemini-cartesia-native
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$(pwd)/../../..:$PYTHONPATH"
cp .env.example .env
python server.py
```

- Listen: `0.0.0.0:8000`
- WebSocket: `/ws?sample-rate=8000`

## Audio notes

| Stage | Expectation |
|-------|-------------|
| Exotel | PCM16 LE mono; typical PSTN `sample-rate=8000` |
| Deepgram STT | Bot upsamples/downsamples to **16 kHz WAV** before `nova-2` listen |
| Cartesia TTS | Requests **raw `pcm_s16le`** at the **call sample rate** (no extra resample) |

If Cartesia rejects the rate, confirm your account supports 8 kHz output or run AgentStream at `16000`.

## Connect Voice AI test

```bash
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_NGROK_HOST/ws?sample-rate=8000"
```

See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).

## Troubleshooting

| Symptom | Likely cause | What to check |
|---------|--------------|---------------|
| Greeting never plays | `CARTESIA_API_KEY` / voice id | Logs: `greeting TTS failed`; Cartesia dashboard key + voice UUID |
| User speech ignored | Silence gate / low RMS | Speak longer than `min_speech`; lower `VAD_RMS_THRESHOLD` |
| Empty transcripts | Deepgram auth or tiny buffer | `DEEPGRAM_API_KEY`; ensure caller audio reaches `/ws` |
| Gemini 403 / empty reply | Bad `GOOGLE_API_KEY` or model name | Try `GEMINI_MODEL=gemini-2.0-flash`; enable Generative Language API |

## References

| Resource | URL |
|----------|-----|
| Deepgram Listen (pre-recorded) | https://developers.deepgram.com/docs/pre-recorded-audio |
| Gemini generateContent | https://ai.google.dev/api/generate-content |
| Cartesia TTS bytes | https://docs.cartesia.ai/api-reference/tts/tts |
| Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
