# Latency and pitch notes (Connect Voice AI)

Reference notes for the three Agent-Stream sample bridges. Values move with network and provider load; use them as a sanity check, not an SLA.

## Formats

| Bridge | Exotel (phone) | Provider wire | Notes |
|--------|----------------|---------------|--------|
| **Sarvam** | 8 kHz PCM16 | Sarvam HTTP STT/TTS | Greeting cached at process boot |
| **OpenAI Realtime** | 8 kHz PCM16 | PCM16 @ **24 kHz** | Bridge resamples both ways; do not use linear PCM at 8 kHz on OpenAI |
| **ElevenLabs** | 8 kHz PCM16 | Often `pcm_16000` | Prefer agent **`pcm_8000`** to skip resample |

## Time to first audio

| Bridge | Typical first media | Notes |
|--------|---------------------|--------|
| **Sarvam** | Under ~1 s (often near 0 with cache hit) | Cached greeting only; generative TTS still ~1–2 s |
| **OpenAI** | Near 0 with `INSTANT_GREETING`; else ~1.5–3 s | Instant path uses TTS-1 cache, then Realtime for turns |
| **ElevenLabs** | ~1–2 s | Depends on ConvAI session + first agent audio |

Outbound framing: Sarvam shared helper ~100 ms frames; OpenAI sample defaults to 200 ms / 3200-byte frames (Exotel minimum chunk size); ElevenLabs paces outbound media so the receive loop stays free.

## Pitch

Low or “slow” voice almost always means **sample-rate mismatch** (for example 16 kHz or 24 kHz PCM played as 8 kHz). Fixes in the samples:

- OpenAI: negotiate PCM 24 kHz with the API; resample to Exotel 8 kHz with stateful rate conversion
- ElevenLabs: resample 16→8 when needed, or set `pcm_8000` on the agent
- Sarvam: synthesize and send at the AgentStream rate (default 8000)

## Limits vs a sub-1s generative goal

Cached greetings can meet sub-1s. Fully generative first speech from OpenAI or ElevenLabs is usually above 1 s unless you pre-roll audio or cache a first utterance (OpenAI sample does this with `INSTANT_GREETING`).
