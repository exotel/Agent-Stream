# Latency and pitch notes (live Connect)

Measured 2026-08-11 against Exotel Connect Voice AI (`+917411179773`).

| Bridge | first_audio_ms | Call duration | Pitch / format | Notes |
|--------|----------------|---------------|----------------|-------|
| **Sarvam** | **0** (cache hit) | 38s | 8 kHz PCM; cache hit + STT turn OK | Greeting pre-warmed at boot. Generative reply TTS still ~1–2s HTTP. |
| **OpenAI** | **2569** (model speech) | 40s | `audio/pcmu` ↔ 8 kHz | Speech TTFA is provider Realtime; test tone on connect is earlier. Pitch OK with pcmu (no 24k→8k bug). |
| **ElevenLabs** | **1513** | 31s | Resample 16→8 kHz | `pcm_16000` negotiated; tip logged to prefer `pcm_8000`. Pitch OK with resample. |

## Limits vs &lt;1s goal

- **Sarvam greeting:** meets &lt;1s via process-boot cache (`first_audio_ms=0`).
- **OpenAI / ElevenLabs first speech:** typically 1.5–3s (provider TTS after session). Sub-1s needs local pre-roll or agent-side cached first message; not claimed for generative path.

## Pitch

Low pitch was sample-rate mismatch (higher-rate PCM played as 8 kHz). Fixes: OpenAI default 8 kHz + correct pcmu wire rate; Sarvam duration heuristic for raw 24 kHz; ElevenLabs 16↔8 resample driven by `start.media_format.sample_rate`.
