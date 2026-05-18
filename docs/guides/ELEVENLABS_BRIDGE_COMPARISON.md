# Two Ways to Bridge Exotel and ElevenLabs

**What the diff tells you about production voice AI on telephony**

*By Saurabh Sharma*

---

We open-sourced Agent-Stream as a framework for building voice bots on Exotel. The ElevenLabs integration is one of **seven bot implementations** in this repo — OpenAI Realtime, Gemini Speech-to-Speech, Gemini Live, pipeline bots, and others. The goal: let developers evaluate AI providers side by side without writing WebSocket plumbing from scratch.

A few months later, a contributor shipped something different: the **production Python bridge** (upstream: [Jitendra2603/exotel-elevenlabs-bridge](https://github.com/Jitendra2603/exotel-elevenlabs-bridge), vendored in this repo at [`bridges/elevenlabs-production/`](../../bridges/elevenlabs-production/)). Same problem — bridge Exotel's phone network to ElevenLabs Conversational AI — but a different philosophy. Single-purpose. Python. Production-first. With features the Node.js framework does not have and does not try to have.

**Contributor:** [Jitendra](https://github.com/Jitendra2603) — see [ATTRIBUTION.md](../../bridges/elevenlabs-production/ATTRIBUTION.md).

Both repos solve the same core problem. The diff between them is, I think, the most honest description of what **"production"** actually means for voice AI on telephony.

---

## What both repos do

At the protocol level, both implement the same thing: a **duplex WebSocket bridge**.

- One connection faces **Exotel**, carrying raw PCM audio from the phone call.
- One connection faces **ElevenLabs**, carrying audio formatted for their Conversational AI API.
- Events flow both ways — caller audio to ElevenLabs, agent audio back to the caller.

The core pattern in Agent-Stream (Node.js):

```javascript
// Exotel "media" → ElevenLabs "user_audio_chunk"
if (exotelEvent.event === 'media' && exotelEvent.media) {
  return { user_audio_chunk: exotelEvent.media.payload };
}
```

That's the bridge at its simplest. The Python repo does the same. The implementations diverge everywhere else.

---

## The technical difference nobody documents: audio resampling

The thing that surprised me most when comparing both repos carefully: **audio resampling**.

| | **Agent-Stream** (`examples/elevenlabs-bridge.js`) | **exotel-elevenlabs-bridge** (Python) |
|---|---------------------------------------------------|----------------------------------------|
| Exotel input | 8 kHz PCM | 8 kHz PCM |
| To ElevenLabs | Resample **8 kHz → 16 kHz** | **Passthrough** at 8 kHz |
| From ElevenLabs | Resample **16 kHz → 8 kHz** | **Passthrough** at 8 kHz |
| Format negotiation | Explicit `output_format: pcm_16000` in init | Reads `agent_output_audio_format` from metadata; no resample |

Agent-Stream is **defensive**: it assumes ElevenLabs wants 16 kHz and converts every chunk bidirectionally.

The Python bridge is **pragmatic**: it forwards base64 PCM as-is and logs negotiated formats from `conversation_initiation_metadata`.

**One of these is correct for production. I'm not certain which.**

The Python bridge works in the wild — teams have deployed it. That implies ElevenLabs often matches output rate to input, or accepts 8 kHz for telephony. But if that behavior changes, passthrough could produce wrong playback speed with no obvious error. Agent-Stream trades a bit of CPU/latency for predictability.

### Before you ship on the Python bridge

1. Log `conversation_initiation_metadata` → `user_input_audio_format` and `agent_output_audio_format`.
2. Align your ElevenLabs agent configuration with **8 kHz** telephony if you stay on passthrough.
3. Run a test call and verify pitch/speed (wrong sample rate = chipmunk or slow motion).

If formats do not match, fix the agent config or add the same resampling path Agent-Stream uses.

---

## The production gap

What the Python bridge has that Agent-Stream does not (today):

### Background sound

When the agent is thinking, there is silence. On a phone call, silence sounds broken. The Python bridge mixes a looping ambient track (office ambience, hold tone, etc.) at the PCM level — during agent speech **and** during silence — so the line never feels dead. This is a small mixing function, not AI. It is **telephony UX**, and it matters.

- Configure: `BG_SOUND_FILE`, `BG_SOUND_VOLUME`
- Control mid-call: `POST /bg-sound` or an ElevenLabs webhook tool

### Regional endpoints

Agent-Stream connects to ElevenLabs' default global API (`api.elevenlabs.io`).

The Python bridge supports:

| Region | WebSocket base |
|--------|----------------|
| `default` | `wss://api.elevenlabs.io` |
| `us` | `wss://api.us.elevenlabs.io` |
| `eu` | `wss://api.eu.residency.elevenlabs.io` |
| **`india`** | `wss://api.in.residency.elevenlabs.io` |

For call centers in India, routing to the nearest region is often the difference between sub-800 ms (natural) and latency that feels like a satellite call. Set `ELEVENLABS_REGION=india`.

### Call transfer

A voice bot that cannot hand off to a human is a demo. The Python bridge wires:

1. ElevenLabs **post-call** webhook → bridge reads `should_transfer` (and team routing)
2. Bridge stores the decision
3. Exotel **Programmable Connect** polls `GET /exotel/connect` → bridge returns the destination number

Three moving parts, already connected.

### Deployment runbooks

The Python repo ships with:

- **AWS ECS Fargate** — ECR, cluster, task definition, ALB, IAM, TLS (DuckDNS + Let's Encrypt)
- **GCP Cloud Run** — `deploy_gcp.sh`
- A documented **anti-pattern**: do not use **AWS App Runner** for this workload — its envoy proxy returns HTTP 403 on WebSocket upgrade ([known limitation](https://github.com/aws/apprunner-roadmap/issues/13))

Exotel requires **`wss://`** with a valid certificate; self-signed certs are rejected.

---

## Framework vs. service

| | **Agent-Stream** | **exotel-elevenlabs-bridge** |
|---|------------------|------------------------------|
| Model | **Base class you extend** (`ExotelWSSServer`) | **Service you configure** (`BridgeConfig` + env vars) |
| Best for | Learning the protocol, comparing providers, custom bots | ElevenLabs-only production on PSTN |
| Run | `npm run elevenlabs-bot` | `gunicorn` / Docker on port `10002` |
| Exotel WebSocket URL | `wss://host:5001/media` | `wss://host:10002/v1/convai/conversation/exotel` or `/media` |
| Language | Node.js | Python |

Both are valid. Which you want depends on whether you are **evaluating providers** or **shipping to production**.

---

## What this tells us about building voice AI

The features that make voice AI **production-ready on telephony** have almost nothing to do with the model.

Connecting to ElevenLabs, streaming audio, handling responses — is on the order of **~100 lines** in either repo. Both have it. It is not the hard part.

The hard part is:

- Background sound so silence does not sound broken
- Regional routing so latency does not feel robotic
- Call transfer so the bot is not a dead end
- TLS and WebSocket hosting that stays up

These are **telephony**, **infrastructure**, and **UX** problems. They existed before LLMs and they will exist after.

---

## Recommended path

### Phase 1 — Learn and compare (Agent-Stream)

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream
git checkout nodejs-voice-bot-framework
npm install
cp .env.example .env   # ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID
npm run elevenlabs-bot
```

Point your Exotel Voicebot applet at `wss://your-host:5001/media`.

Use this repo to understand events, barge-in (`clear`), custom query params, and to compare OpenAI Realtime vs ElevenLabs vs pipeline bots.

### Phase 2 — Production ElevenLabs (Python bridge)

**In this repo** (recommended for Exotel customers):

```bash
cd bridges/elevenlabs-production
python3 -m venv ../../.venv-elevenlabs-bridge
source ../../.venv-elevenlabs-bridge/bin/activate
pip install -r exotel/requirements.txt

export ELEVENLABS_AGENT_ID="..."
export ELEVENLABS_API_KEY="..."
export ELEVENLABS_REGION="india"          # if calls are from India
export BG_SOUND_FILE="exotel/assets/office-ambience-loud.wav"
export BG_SOUND_VOLUME="0.3"

python3 exotel/bridge.py --port 10002
```

See [`bridges/elevenlabs-production/README.md`](../../bridges/elevenlabs-production/README.md) and [`ATTRIBUTION.md`](../../bridges/elevenlabs-production/ATTRIBUTION.md).

**Upstream** (for contributing back): https://github.com/Jitendra2603/exotel-elevenlabs-bridge

Deploy with `deploy_aws.sh` or `deploy_gcp.sh` in that directory. Configure Exotel:

`wss://your-domain/v1/convai/conversation/exotel?agent_id=<agent_id>`

### Decision matrix

| You need… | Use |
|-----------|-----|
| Compare OpenAI / Gemini / ElevenLabs | **Agent-Stream** |
| Custom bot logic, new provider hooks | **Agent-Stream** (subclass `ExotelWSSServer`) |
| Lowest latency | Agent-Stream `npm run openai-realtime` (~500 ms) |
| Best ElevenLabs voice + safe 8↔16 kHz handling | **Agent-Stream** ElevenLabs bridge |
| India region, ambience, transfer, ECS runbooks | **exotel-elevenlabs-bridge** |
| Node-only team, no Python ops | **Agent-Stream** + plan to port production features |

---

## Side-by-side reference

| Dimension | Agent-Stream | exotel-elevenlabs-bridge |
|-----------|--------------|--------------------------|
| Scope | 7 bots, full framework | ElevenLabs only |
| Audio | 8 kHz ↔ 16 kHz resample | 8 kHz passthrough |
| ElevenLabs regions | Default API | default, us, eu, **india** |
| Background ambience | No | Yes |
| Post-call transfer | No | Yes |
| Per-call transcript files | No | Yes |
| Tests / multi-provider docs | Extensive | Deployment-focused |
| Maintainer | Exotel (this repo) | Community ([Jitendra2603](https://github.com/Jitendra2603/exotel-elevenlabs-bridge)) |

---

## One line

**Start with Agent-Stream to understand the protocol. Deploy the Python bridge when you need production telephony features. Read both carefully — the audio format difference is real and will eventually matter.**

---

## Related docs in this repo

- [ElevenLabs section in README](../../README.md#elevenlabs-conversational-ai) — setup for `npm run elevenlabs-bot`
- [WebSocket protocol](../reference/WEBSOCKET_PROTOCOL.md) — Exotel events
- [Latency optimization](./LATENCY_OPTIMIZATION.md)
- [Best practices](./BEST_PRACTICES.md)
- [Exotel integration issues](../troubleshooting/EXOTEL_INTEGRATION_ISSUES.md)

## External

- [exotel-elevenlabs-bridge (upstream)](https://github.com/Jitendra2603/exotel-elevenlabs-bridge)
- [ElevenLabs Conversational AI docs](https://elevenlabs.io/docs/conversational-ai/overview)
