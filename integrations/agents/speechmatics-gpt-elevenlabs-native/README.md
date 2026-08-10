# Speechmatics + GPT + ElevenLabs (native pipeline)

Turn-based phone agent on Exotel AgentStream:

**Speechmatics Batch STT → OpenAI Chat Completions → ElevenLabs Flash TTS**

STT is implemented in this recipe’s `agent.py` against the Speechmatics **Jobs** API (WAV upload + poll). The shared `stt_speechmatics` helper remains a placeholder and is **not** used. Batch STT latency is **not yet benchmarked**; prefer Speechmatics Realtime WebSocket for production low-latency.

## Architecture

```text
Caller ↔ Exotel AgentStream (PCM16 WSS)
         ↕ /ws?sample-rate=8000
This bot
  → Speechmatics POST /v2/jobs (WAV @ 16 kHz) → poll → transcript
  → OpenAI /v1/chat/completions
  → ElevenLabs TTS (pcm_16000) → resample to call rate
  → Exotel media frames
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `SPEECHMATICS_API_KEY` | Yes | Bearer token for Jobs API |
| `SPEECHMATICS_LANGUAGE` | No | Default `en` |
| `SPEECHMATICS_MODEL` | No | Operating point, default `enhanced` |
| `SPEECHMATICS_BATCH_URL` | No | Default `https://asr.api.speechmatics.com/v2/jobs` |
| `OPENAI_API_KEY` | Yes | Chat Completions |
| `OPENAI_MODEL` | No | Default `gpt-4.1-mini` |
| `ELEVENLABS_API_KEY` | Yes | TTS HTTP API |
| `ELEVENLABS_VOICE_ID` | No | Voice id |
| `ELEVENLABS_MODEL_ID` | No | Default `eleven_flash_v2_5` |
| `SERVER_PORT` | No | Default `8000` |

## Quick start

```bash
cd integrations/agents/speechmatics-gpt-elevenlabs-native
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
| Speechmatics | **16 kHz WAV** multipart upload; language via `SPEECHMATICS_LANGUAGE` |
| ElevenLabs | **`pcm_16000`** then resample to AgentStream rate |

EU / other regional ASR hosts can be set with `SPEECHMATICS_BATCH_URL` if your account is not on the default SaaS endpoint.

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
| Job `rejected` | Bad language / operating point / entitlement | Portal job details; try `SPEECHMATICS_MODEL=standard` |
| Long silence after user talk | Batch poll waiting | Expected for Jobs API; check job status in logs |
| ElevenLabs 401 | Key / voice mismatch | Voice must belong to the same ElevenLabs account as the key |
| Empty transcript text | Too-short utterance | Increase speech before silence; lower `VAD_RMS_THRESHOLD` |

## References

| Resource | URL |
|----------|-----|
| Speechmatics Batch quickstart | https://docs.speechmatics.com/speech-to-text/batch/quickstart |
| Speechmatics auth | https://docs.speechmatics.com/get-started/authentication |
| OpenAI Chat Completions | https://platform.openai.com/docs/api-reference/chat |
| ElevenLabs TTS | https://elevenlabs.io/docs/api-reference/text-to-speech |
| Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
