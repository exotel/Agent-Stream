# Deepgram + GPT + Grok TTS (native pipeline)

Turn-based phone agent on Exotel AgentStream:

**Deepgram Nova (STT) → OpenAI Chat Completions (LLM) → xAI Grok Text-to-Speech**

Grok TTS is called from this recipe’s `agent.py` with the documented REST body (`voice_id`, `language`, `output_format.codec=pcm`). End-to-end latency is **not yet benchmarked**.

## Architecture

```text
Caller ↔ Exotel AgentStream (PCM16 WSS)
         ↕ /ws?sample-rate=8000
This bot
  → Deepgram /v1/listen (WAV @ 16 kHz)
  → OpenAI /v1/chat/completions
  → xAI POST /v1/tts (codec=pcm @ call rate)
  → Exotel media frames
```

## Prerequisites

| Variable | Required | Purpose |
|----------|----------|---------|
| `DEEPGRAM_API_KEY` | Yes | Deepgram listen |
| `OPENAI_API_KEY` | Yes | Chat Completions |
| `OPENAI_MODEL` | No | Default `gpt-4.1-mini` |
| `XAI_API_KEY` | Yes | Grok TTS Bearer token |
| `GROK_TTS_VOICE` | No | Voice id (default `eve`) |
| `GROK_TTS_LANGUAGE` | No | BCP-47 / `en` (default `en`) |
| `SERVER_PORT` | No | Default `8000` |
| `SYSTEM_PROMPT` / `GREETING_TEXT` | No | Prompt / greeting |

`GROK_TTS_MODEL` is accepted in `.env` for older templates but is **not** sent to `/v1/tts` (voice is selected via `voice_id`).

## Quick start

```bash
cd integrations/agents/deepgram-gpt-groktts-native
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
| Deepgram | **16 kHz WAV** to `nova-2` |
| Grok TTS | REST `output_format`: `codec=pcm`, `sample_rate` = AgentStream rate (`8000` / `16000` / `24000`) |

Do not confuse this recipe with **Grok Voice** (`grok-voice-native`), which is full speech-to-speech over the Realtime WebSocket.

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
| TTS HTTP 4xx | Missing `language` / bad `voice_id` | Set `GROK_TTS_LANGUAGE=en`, voice lowercase (`eve`, `ara`, `sal`, …) |
| Greeting is silence | Old shared helper behavior | Confirm you are on this recipe’s `tts_grok_rest` (see `agent.py`) |
| Deepgram empty | Key or silence gate | Logs `user:`; verify token `Authorization: Token …` |
| OpenAI error | Billing / model name | `OPENAI_MODEL` available on your account |

## References

| Resource | URL |
|----------|-----|
| Deepgram Listen | https://developers.deepgram.com/docs/pre-recorded-audio |
| OpenAI Chat Completions | https://platform.openai.com/docs/api-reference/chat |
| xAI Text to Speech | https://docs.x.ai/developers/model-capabilities/audio/text-to-speech |
| Connect Voice AI | https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api |
| AgentStream WSS | [docs/AGENTSTREAM_WSS_PROTOCOL.md](../../../docs/AGENTSTREAM_WSS_PROTOCOL.md) |
