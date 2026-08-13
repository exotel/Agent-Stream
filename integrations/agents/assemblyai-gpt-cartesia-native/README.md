# AssemblyAI + GPT + Cartesia (native pipeline)

Turn-based phone agent on Exotel AgentStream:

**AssemblyAI (STT) → OpenAI Chat Completions (LLM) → Cartesia Sonic (TTS)**

Uses upload + poll transcription (`speech_model=universal`). Batch STT adds turn latency vs streaming ASR — **not yet benchmarked**.

## Architecture

```text
Caller ↔ Exotel AgentStream (PCM16 WSS)
         ↕ /ws?sample-rate=8000
This bot
  → AssemblyAI upload → transcript poll
  → OpenAI /v1/chat/completions
  → Cartesia /tts/bytes (raw pcm_s16le @ call rate)
  → Exotel media frames
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `ASSEMBLYAI_API_KEY` | Yes | AssemblyAI auth header |
| `OPENAI_API_KEY` | Yes | Chat Completions |
| `OPENAI_MODEL` | No | Default `gpt-4.1-mini` |
| `CARTESIA_API_KEY` | Yes | Cartesia TTS |
| `CARTESIA_VOICE_ID` | No | Voice UUID |
| `CARTESIA_MODEL` | No | Default `sonic-english` |
| `SERVER_PORT` | No | Default `8000` |
| `SYSTEM_PROMPT` / `GREETING_TEXT` | No | Prompt / greeting |

## Quick start

```bash
cd integrations/agents/assemblyai-gpt-cartesia-native
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
| Exotel | PCM16 LE mono |
| AssemblyAI | Bot sends **16 kHz WAV** via `/v2/upload`, then creates a transcript job |
| Cartesia | Raw **`pcm_s16le`** at the AgentStream sample rate |

AssemblyAI’s streaming Realtime API is **not** used here; each user turn is a short batch job. Prefer longer silence gaps if you hear cut-off phrases.

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
| Stuck after user speaks | Transcript still polling / error status | Logs `pipeline turn failed`; AssemblyAI job error field |
| Greeting fails | Cartesia credentials | `CARTESIA_API_KEY`, voice id region |
| GPT refusals / empty | Model or prompt | `OPENAI_MODEL`, `SYSTEM_PROMPT` |
| No barge-in mid-reply | Pipeline sets `_busy` during TTS | Expected for this scaffold; swap to streaming VAD for production |

## References

| Resource | URL |
|----------|-----|
| AssemblyAI upload + transcript | https://www.assemblyai.com/docs/api-reference/transcripts |
| OpenAI Chat Completions | https://platform.openai.com/docs/api-reference/chat |
| Cartesia TTS | https://docs.cartesia.ai/api-reference/tts/tts |
| Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
