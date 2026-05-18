# Agent-Stream Bridges

Optional **production-oriented** integrations that complement the Node.js framework in the repo root.

| Path | Language | Purpose |
|------|----------|---------|
| [`elevenlabs-production/`](elevenlabs-production/) | Python | Exotel ↔ ElevenLabs with India region, background ambience, call transfer, ECS/GCP deploy |

## Node.js (framework) vs Python (production bridge)

| | **Root repo** (`npm run elevenlabs-bot`) | **`bridges/elevenlabs-production/`** |
|---|------------------------------------------|--------------------------------------|
| Use when | Learning Exotel protocol, comparing AI providers | Shipping ElevenLabs-only voice on PSTN |
| Audio | 8 kHz ↔ 16 kHz resample | 8 kHz passthrough |
| Run | `npm run elevenlabs-bot` | See [elevenlabs-production/README.md](elevenlabs-production/README.md) |

See [docs/guides/ELEVENLABS_BRIDGE_COMPARISON.md](../docs/guides/ELEVENLABS_BRIDGE_COMPARISON.md) for the full comparison.

## Attribution

The Python production bridge was written by **Jitendra** and imported via git subtree. See [elevenlabs-production/ATTRIBUTION.md](elevenlabs-production/ATTRIBUTION.md).
