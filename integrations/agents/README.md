# Exotel Voice Agent Recipes

Production-oriented **AgentStream** recipes: pick a Voice AI stack, run a FastAPI WebSocket server, and connect phone audio with [Connect Voice AI](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api) (`StreamType=bidirectional`).

Telephony is always **Exotel AgentStream** (PCM16 over WSS). Only the AI providers change.

```text
Phone ←→ Exotel AgentStream ←WSS→ FastAPI bot ←→ Voice AI (S2S or STT+LLM+TTS)
```

## What Exotel can provide to users

### Speech-to-speech (native realtime)

| Recipe | Model | Notes | Path |
|--------|-------|-------|------|
| GPT Realtime | OpenAI Realtime | Barge-in, low latency | [`gptrealtime-native`](gptrealtime-native/) · also [`../openai-realtime`](../openai-realtime/) |
| Gemini Live | Google Gemini Live | Function calling, multilingual | [`gemini-live-native`](gemini-live-native/) · also [`../gemini-live`](../gemini-live/) |
| Gemini Live + Pipecat | Gemini Live | Modular VAD / pipeline | [`gemini-live-pipecat`](gemini-live-pipecat/) |
| Grok Voice | xAI Grok Voice | S2S with VAD / barge-in | [`grok-voice-native`](grok-voice-native/) |

### STT + LLM + TTS pipelines

| Recipe | STT | LLM | TTS | Path |
|--------|-----|-----|-----|------|
| Deepgram + Gemini + Cartesia | Deepgram Nova | Gemini | Cartesia Sonic | [`deepgram-gemini-cartesia-native`](deepgram-gemini-cartesia-native/) |
| Deepgram + Gemini + ElevenLabs | Deepgram Nova | Gemini | ElevenLabs Flash | [`deepgram-gemini-elevenlabs-native`](deepgram-gemini-elevenlabs-native/) |
| Deepgram + GPT + OpenAI TTS (Pipecat) | Deepgram Nova | GPT | OpenAI TTS | [`deepgram-gpt-openaitts-pipecat`](deepgram-gpt-openaitts-pipecat/) · also [`../pipecat`](../pipecat/) |
| AssemblyAI + GPT + Cartesia | AssemblyAI | GPT | Cartesia Sonic | [`assemblyai-gpt-cartesia-native`](assemblyai-gpt-cartesia-native/) |
| Sarvam + GPT + ElevenLabs | Sarvam Saaras | GPT | ElevenLabs | [`sarvam-gpt-elevenlabs-native`](sarvam-gpt-elevenlabs-native/) · helpers in [`../sarvam`](../sarvam/) |
| Speechmatics + GPT + ElevenLabs | Speechmatics Batch | GPT | ElevenLabs | [`speechmatics-gpt-elevenlabs-native`](speechmatics-gpt-elevenlabs-native/) |
| Deepgram + GPT + Grok TTS | Deepgram Nova | GPT | Grok TTS | [`deepgram-gpt-groktts-native`](deepgram-gpt-groktts-native/) |

### Platform / framework bridges (already in catalog)

| Integration | Path | Role |
|-------------|------|------|
| ElevenLabs Conversational | [`../elevenlabs`](../elevenlabs/) | Managed conversational agent + ambience |
| Pipecat + ExotelFrameSerializer | [`../pipecat`](../pipecat/) | Pluggable STT/LLM/TTS |
| Dograh telephony | [`../dograh`](../dograh/) | Exotel as telephony provider inside Dograh |

## Shared pieces

| Path | Purpose |
|------|---------|
| [`_shared/`](_shared/) | AgentStream WSS FastAPI base + PCM helpers |
| [`../../shared/place_connect_call.py`](../../shared/place_connect_call.py) | Outbound Connect Voice AI smoke test |
| [`../../docs/CONNECT_VOICE_AI.md`](../../docs/CONNECT_VOICE_AI.md) | API reference |
| [`../../docs/AGENTSTREAM_WSS_PROTOCOL.md`](../../docs/AGENTSTREAM_WSS_PROTOCOL.md) | WSS events / sample rates |

## Quick test (any recipe)

```bash
cd integrations/agents/<recipe>
cp .env.example .env   # fill AI + optional Exotel keys
pip install -r requirements.txt
python server.py
# ngrok http <port>
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=8000"
```

## Naming

See [CONTRIBUTING.md](CONTRIBUTING.md). Folders use `{llm}-{stt}-{tts}-{orchestration}` for pipelines and `{model}-native` for S2S.
