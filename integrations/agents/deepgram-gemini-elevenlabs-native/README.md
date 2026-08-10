# Deepgram + Gemini + ElevenLabs (native pipeline)

Turn-based phone agent on Exotel AgentStream:

**Deepgram Nova (STT) → Google Gemini (LLM) → ElevenLabs Flash TTS**

Shared `PipelineSession` silence gate. Latency / WER figures are **not yet benchmarked**.

## Architecture

```text
Caller ↔ Exotel AgentStream (PCM16 WSS)
         ↕ /ws?sample-rate=8000
This bot
  → Deepgram /v1/listen (WAV @ 16 kHz)
  → Gemini generateContent
  → ElevenLabs TTS (pcm_16000) → resample to call rate
  → Exotel media frames
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `DEEPGRAM_API_KEY` | Yes | Deepgram listen API |
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `GEMINI_MODEL` | No | Default `gemini-2.0-flash` |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs TTS |
| `ELEVENLABS_VOICE_ID` | No | Default Rachel-style id in shared helper |
| `ELEVENLABS_MODEL_ID` | No | Default `eleven_flash_v2_5` |
| `SERVER_PORT` | No | Default `8000` |
| `SYSTEM_PROMPT` / `GREETING_TEXT` | No | Prompt / greeting |

## Quick start

```bash
cd integrations/agents/deepgram-gemini-elevenlabs-native
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
| Exotel | PCM16 LE mono (`8000` typical) |
| Deepgram | WAV **16 kHz** upload to `nova-2` |
| ElevenLabs | Requested as **`pcm_16000`**, then resampled with `audioop.ratecv` to the AgentStream rate |

Flash models are optimized for low-latency TTS; do not pass Conversational Agent IDs here — this recipe uses the **TTS HTTP API**, not the ConvAI WebSocket bridge under `integrations/elevenlabs/`.

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
| 401 from ElevenLabs | Wrong key or voice id | `ELEVENLABS_API_KEY` + voice belonging to that account |
| Tinny / chipmunk audio | Resample bug or wrong `sample-rate` query | Match ngrok StreamUrl `sample-rate` to what Exotel negotiates |
| No STT text | Deepgram key / silence gate | Logs `user:`; verify Deepgram project has listen access |
| Gemini empty candidates | Safety block or bad model | Inspect API error body; switch `GEMINI_MODEL` |

## References

| Resource | URL |
|----------|-----|
| Deepgram Listen | https://developers.deepgram.com/docs/pre-recorded-audio |
| Gemini API | https://ai.google.dev/api/generate-content |
| ElevenLabs TTS | https://elevenlabs.io/docs/api-reference/text-to-speech |
| Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
