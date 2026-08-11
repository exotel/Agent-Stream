# ElevenLabs Conversational AI + Exotel AgentStream

Connect an Exotel phone call to an [ElevenLabs Conversational AI](https://elevenlabs.io) agent over AgentStream. Audio stays speech-to-speech: Exotel PCM ↔ your bridge ↔ ElevenLabs ConvAI.

Sample code: [`integrations/elevenlabs`](https://github.com/exotel/Agent-Stream/tree/main/integrations/elevenlabs) in the [Agent-Stream](https://github.com/exotel/Agent-Stream) repo.

If you have not set up Connect yet, start with [Connect Voice AI with AgentStream](connect-voice-ai.md).

## What you get

- Outbound (or inbound via applet) calls that talk to your ElevenLabs agent
- Bidirectional PCM on AgentStream
- A production-oriented Python bridge under `integrations/elevenlabs/exotel/bridge.py`

## Before you start

| Item | Notes |
|------|--------|
| ElevenLabs | Agent ID + API key |
| Exotel | Account SID, API Key, API Token, ExoPhone |
| Python 3.10+ | Virtualenv recommended |
| Public WSS | cloudflared or ngrok for the first test |

**Audio tip:** In the ElevenLabs agent, set output to **`pcm_8000`** when available. That avoids a 16→8 kHz resample and reduces “slow” or muddy voice on the phone.

## Minute 0–5 — Install

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream

cp shared/env.exotel.example shared/.env.exotel
# Fill EXOTEL_ACCOUNT_SID, EXOTEL_API_KEY, EXOTEL_API_TOKEN, EXOTEL_CALLER_ID

cd integrations/elevenlabs
python3 -m venv venv && source venv/bin/activate
pip install -r exotel/requirements.txt

export ELEVENLABS_AGENT_ID="your_agent_id"
export ELEVENLABS_API_KEY="your_api_key"
export ELEVENLABS_REGION="default"   # default | us | eu | india
export BG_SOUND_VOLUME="0"           # 0 = no background ambience while testing
```

## Minute 5–10 — Run the bridge and open a tunnel

Terminal A:

```bash
cd integrations/elevenlabs
source venv/bin/activate
python exotel/bridge.py --port 10002 \
  --agent-id "$ELEVENLABS_AGENT_ID" \
  --api-key "$ELEVENLABS_API_KEY"
```

The bridge listens on `0.0.0.0:10002`. Path: `/v1/convai/conversation/exotel`.

Terminal B:

```bash
cloudflared tunnel --url http://127.0.0.1:10002
# Note the https://….trycloudflare.com host — use wss:// with the same host
```

## Minute 10–15 — Place a Connect call

From the **repo root**:

```bash
set -a && source shared/.env.exotel && set +a

python shared/place_connect_call.py \
  --to +91XXXXXXXXXX \
  --stream-url "wss://YOUR_CLOUDFLARE_HOST/v1/convai/conversation/exotel"
```

| | |
|--|--|
| **StreamUrl** | `wss://HOST/v1/convai/conversation/exotel` |
| **Port** | `10002` |

Answer the handset. The agent should greet at normal pitch and respond when you speak.

## Verify

- Voice is not slow or unusually deep (if it is, set agent output to `pcm_8000` or confirm resample logs).
- Bridge logs show media flowing and a `first_audio_ms=…` style line when audio starts.
- Call lasts well beyond a few seconds (very short hangups usually mean a bad StreamUrl or the receive loop blocked).

## Go-live checklist

- [ ] Bridge runs on a stable host with a real TLS certificate for `wss://`
- [ ] API keys only in env / secret store
- [ ] Agent audio format set for telephony (`pcm_8000` preferred)
- [ ] Background sound volume set intentionally (or `0`)
- [ ] Monitoring on process health and WebSocket disconnects
- [ ] Load-tested concurrent calls for your expected traffic

This sample is a solid bridge for pilots. High concurrency still needs horizontal scale (multiple bridge instances behind a WSS load balancer), timeouts, and ops metrics.

## Troubleshoot

| Symptom | What to check |
|---------|----------------|
| Call drops in ~4 seconds | StreamUrl path wrong; tunnel down; bot not accepting WSS |
| Slow / deep voice | Agent still on 16 kHz PCM played as 8 kHz — prefer `pcm_8000` or confirm bridge resample |
| Agent parrots the caller | Prompt / conversation override and half-duplex behaviour in the bridge README |
| No agent audio | API key, agent ID, region, and ElevenLabs console errors |

## Related

- Repo README: `integrations/elevenlabs/README.md`
- [Connect Voice AI API](https://docs.exotel.com/exotel-agentstream/connect-voice-ai-api)
- [OpenAI Realtime guide](openai-realtime.md) · [Sarvam guide](sarvam.md)
