# Dograh + Exotel AgentStream

Native Exotel telephony provider package for [dograh-hq/dograh](https://github.com/dograh-hq/dograh).

This is **platform wiring** (Exotel as a telephony provider inside Dograh), not a standalone Voice AI vendor bot. For AI bridges, see sibling folders under `integrations/`.

| Path | Purpose |
| --- | --- |
| `providers/exotel/` | Drop-in Dograh provider package |
| `WIRING.md` | One-line edits required in Dograh |
| `tests/test_provider.py` | Unit tests for Calls/connect |
| `DOGRAH_AGENTSTREAM_INTEGRATION.md` | Scope, checklist, copy paths |

## Copy into Dograh

See [WIRING.md](WIRING.md). Source paths are under `integrations/dograh/`.

## Connect Voice AI

Dograh’s Exotel provider uses the same [Calls/connect](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api) API. To smoke-test Connect without Dograh:

```bash
python ../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_DOGRAH_OR_BRIDGE_HOST/..."
```

See [docs/CONNECT_VOICE_AI.md](../../docs/CONNECT_VOICE_AI.md).
