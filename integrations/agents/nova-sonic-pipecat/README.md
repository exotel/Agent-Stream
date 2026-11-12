# Amazon Nova Sonic + Pipecat on Exotel AgentStream

Speech-to-speech voice agent: phone calls on Exotel, conversation by **Amazon Nova Sonic** (Bedrock),
glued together by Pipecat's `ExotelFrameSerializer` and `AWSNovaSonicLLMService`.

```text
Phone ←→ Exotel AgentStream ←WSS (PCM16)→ server.py (Pipecat) ←Bedrock bidirectional stream→ Nova Sonic
```

What you get without writing protocol code:

- AgentStream events (`connected` / `start` / `media` / `clear` / `stop`), outbound media sent in
  AgentStream-safe chunks (≥ 100 ms, multiple of 320 bytes)
- Resampling between the call rate (8 / 16 / 24 kHz) and Nova (16 kHz in, 24 kHz out)
- Barge-in: when the caller talks over the bot, Nova's interruption becomes an Exotel `clear`
- Calls longer than Nova's ~8-minute connection limit: Pipecat's session continuation hands over
  to a fresh Nova session with the conversation carried across

## AWS prerequisites

| Need | Detail |
|------|--------|
| Region | A region where Nova Sonic is available on Bedrock (e.g. `us-east-1`). Pick the one nearest your Exotel region for latency. |
| Model access | `amazon.nova-2-sonic-v1:0` (or a newer Nova Sonic model ID) enabled in that region, not blocked by an SCP |
| IAM | `bedrock:InvokeModel` and `bedrock:InvokeModelWithBidirectionalStream` on `arn:aws:bedrock:<region>::foundation-model/<model-id>` |
| Credentials | Instance/task role (recommended), AWS profile/SSO, or keys in `.env` |
| Quota | Concurrent bidirectional streams ≥ concurrent calls (one stream per call) |

Without keys in `.env`, credentials come from `aws configure export-credentials`, so the AWS CLI v2 must be installed.

## Run

```bash
cd integrations/agents/nova-sonic-pipecat
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # AWS region / keys, model, voice
python test_offline.py          # no AWS, no call: must print PASS
python server.py                # :8765
# ngrok http 8765  ->  wss://<id>.ngrok-free.app
```

WebSocket: `/ws?sample-rate=16000` (8000 and 24000 also work; 16000 matches Nova's input).

## Connect Voice AI

```bash
python ../../../shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_HOST/ws?sample-rate=16000"
```

Connect Voice AI: `StreamType=bidirectional`, `StreamUrl=wss://YOUR_HOST/ws?sample-rate=16000`.
For inbound calls, put the same URL in a **Voicebot applet** in App Bazaar and assign your ExoPhone to the flow.
See [docs/CONNECT_VOICE_AI.md](../../../docs/CONNECT_VOICE_AI.md).

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` | empty | Optional; empty uses the default AWS chain |
| `NOVA_MODEL` | `amazon.nova-2-sonic-v1:0` | Nova Sonic model ID |
| `NOVA_VOICE` | `matthew` | Voice ID; pick one that matches the caller's language |
| `NOVA_ENDPOINTING` | `MEDIUM` | `LOW` / `MEDIUM` / `HIGH`: how quickly Nova decides the caller has finished |
| `SYSTEM_PROMPT` | `system_prompt.md` | Agent instructions |
| `EXOTEL_SAMPLE_RATE` | `16000` | Used only if the StreamUrl has no `?sample-rate=` |
| `SERVER_HOST` / `SERVER_PORT` | `0.0.0.0` / `8765` | Listen address |

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `AccessDeniedException` in logs | Model access in that region, IAM actions above, SCPs |
| Silence after answer | Server log shows `call start`? If not, the StreamUrl isn't reachable over `wss://` |
| Bot cuts the caller off / waits too long | Tune `NOVA_ENDPOINTING` |
| High latency | Bedrock region far from the call; host the server near both |
