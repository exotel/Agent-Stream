# AgentStream WebSocket protocol

Shared edge protocol for every bridge under [`integrations/`](../integrations/). Exotel opens a WebSocket to your `StreamUrl` and exchanges JSON control events plus base64 PCM audio.

See also: [Connect Voice AI](CONNECT_VOICE_AI.md) · [AgentStream docs](https://docs.exotel.com/exotel-agentstream/get-started-with-exotel-agentstream)

## Audio

| Property | Value |
|----------|--------|
| Encoding | 16-bit linear PCM (not μ-law) |
| Channels | Mono |
| Sample rate | `8000` (default), `16000`, or `24000` via `?sample-rate=` on the URL |
| Direction | Bidirectional when `StreamType=bidirectional` |

## Typical events

Exact field names can vary slightly by applet / Connect path; bridges should tolerate missing optional fields.

| Event | Direction | Role |
|-------|-----------|------|
| `connected` | Exotel → bot | WebSocket accepted |
| `start` | Exotel → bot | Stream / call metadata (`streamSid`, `callSid`, from/to when present) |
| `media` | both | Base64 PCM payload |
| `mark` | both | Playback / sync markers |
| `clear` | bot → Exotel | Drop queued playback (barge-in) |
| `stop` | Exotel → bot | Stream ending |

## Bot responsibilities

1. Accept WSS; parse `sample-rate` from the query string when present.
2. After `start`, bridge audio to the Voice AI provider.
3. Send `media` frames back for TTS / realtime speech.
4. On user interrupt, send `clear` if the provider signals barge-in.
5. Close the socket to hang up (Exotel has no automatic hang-up from the serializer side in Pipecat).

## Testing without a phone

```bash
# After starting a bridge locally
wscat -c "ws://localhost:5000/?sample-rate=8000"
# Send: {"event":"connected"}
```

For a real PSTN leg, use [Connect Voice AI](CONNECT_VOICE_AI.md) and `shared/place_connect_call.py`.
