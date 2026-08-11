# AgentStream pages for docs.exotel.com

Paste these into [Exotel AgentStream](https://docs.exotel.com/exotel-agentstream) (Archbee). Runnable code lives in this repo under `integrations/`.

## Suggested nav under AgentStream

1. Overview and Connect Voice AI — [connect-voice-ai.md](connect-voice-ai.md)
2. ElevenLabs Conversational AI — [elevenlabs.md](elevenlabs.md)
3. OpenAI Realtime — [openai-realtime.md](openai-realtime.md)
4. Cartesia Line — [cartesia-line.md](cartesia-line.md)
5. Sarvam STT/TTS — [sarvam.md](sarvam.md)
6. Pipecat modular pipeline — [pipecat.md](pipecat.md)
7. Latency notes (internal) — [LATENCY_NOTES.md](LATENCY_NOTES.md)

## What each integration folder solves

| Folder | Problem it solves |
|--------|-------------------|
| [`integrations/elevenlabs`](../../integrations/elevenlabs) | Bridge Exotel phone audio to an ElevenLabs ConvAI agent (speech-to-speech). |
| [`integrations/openai-realtime`](../../integrations/openai-realtime) | Bridge Exotel to OpenAI Realtime GA (speech-to-speech, 24 kHz wire, 8 kHz on the phone). |
| [`integrations/agents/cartesia-line-native`](../../integrations/agents/cartesia-line-native) | Bridge Exotel to a Cartesia Line managed agent over the Agents WebSocket API. |
| [`integrations/sarvam`](../../integrations/sarvam) | Sarvam Saaras STT + Bulbul TTS over AgentStream (cascaded, good for Indian languages). |
| [`integrations/pipecat`](../../integrations/pipecat) | Pipecat + ExotelFrameSerializer: pluggable Deepgram → OpenAI → Cartesia (or swap stages). |
| [`shared/place_connect_call.py`](../../shared/place_connect_call.py) | Place a Connect Voice AI test call without building your own API client. |

Keep StreamUrl paths in sync with the provider READMEs when you edit either side.
