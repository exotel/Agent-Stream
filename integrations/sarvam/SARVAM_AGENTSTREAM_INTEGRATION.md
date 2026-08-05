# Sarvam AI + Exotel Agent Stream — Production Integration Guide

**Branch:** `docs/sarvam-agentstream-integration`  
**Tag:** `Sarvam-AgentStream-Integration-v1.0`  
**Status:** Production reference  
**Last updated:** May 2026

> Build voice AI bots for **Hindi, English, and 10+ Indian languages** on **real PSTN and browser calls** using [Exotel Agent Stream](https://developer.exotel.com/api/agent-stream) for telephony and [Sarvam AI](https://docs.sarvam.ai) for native Indian-language speech.

This guide is the engineering companion to *Building Voice AI Bots for Indian Languages: Exotel Agent Stream + Sarvam AI* and reflects a production-tested **STT → LLM → TTS** pipeline used in booth and field deployments.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Connectivity modes](#4-connectivity-modes)
5. [Voice pipeline](#5-voice-pipeline)
6. [Exotel Agent Stream protocol](#6-exotel-agent-stream-protocol)
7. [Sarvam API integration](#7-sarvam-api-integration)
8. [Reference implementations](#8-reference-implementations)
9. [Production engineering](#9-production-engineering)
10. [Exotel configuration](#10-exotel-configuration)
11. [Deployment](#11-deployment)
12. [Observability](#12-observability)
13. [Performance targets](#13-performance-targets)
14. [Troubleshooting runbook](#14-troubleshooting-runbook)
15. [Security checklist](#15-security-checklist)
16. [Roadmap](#16-roadmap)
17. [References](#17-references)

---

## 1. Executive summary

| Layer | Technology | Role |
|-------|------------|------|
| Telephony / browser | Exotel Agent Stream | SIP, PSTN, WebRTC → single WSS audio bus |
| STT | Sarvam `saaras:v3` | Indian languages, auto-detect |
| LLM | OpenAI `gpt-4o-mini` (or your model) | Reasoning, code-switching in prompt |
| TTS | Sarvam `bulbul:v3` | Natural `hi-IN` / `en-IN` voices |

**Key insight:** The voice bot receives the **same WebSocket PCM stream** whether the caller uses a phone or a browser. Your bot does not branch on connectivity type—only on audio frames and protocol events.

**Typical turn latency:** 1.5–2.5 seconds (REST pipeline). Greeting playback: **&lt;50 ms** when pre-cached.

---

## 2. Architecture

### 2.1 End-to-end flow

```
┌─────────────┐     PSTN/SIP or WebRTC      ┌────────────────────┐
│   Caller    │ ──────────────────────────► │  Exotel Agent      │
│ Phone/Browser│                             │  Stream (WSS)      │
└─────────────┘                             └─────────┬──────────┘
                                                      │ 8 kHz PCM
                                                      │ 20 ms frames
                                            ┌─────────▼──────────┐
                                            │  Your voice bot    │
                                            │  (Node or Python)  │
                                            │                    │
                                            │  Turn detect/VAD   │
                                            │       │            │
                                            │  Sarvam STT (REST) │
                                            │       │            │
                                            │  LLM (REST/WS)     │
                                            │       │            │
                                            │  Sarvam TTS (REST) │
                                            │       │            │
                                            │  Real-time pacing  │
                                            └─────────┬──────────┘
                                                      │
                                            ┌─────────▼──────────┐
                                            │  media → Exotel    │
                                            └────────────────────┘
```

### 2.2 Sample-rate map (critical for production)

| Stage | Sample rate | Notes |
|-------|-------------|--------|
| Exotel telephony | **8 kHz** | 16-bit mono PCM, 320 bytes / 20 ms |
| Sarvam STT input | **16 kHz** | Upsample before STT |
| Sarvam TTS output | **24 kHz** | Request `speech_sample_rate: 24000` |
| Back to Exotel | **8 kHz** | Downsample after TTS |

Getting resampling wrong causes **garbled playback** or **empty transcripts**.

---

## 3. Prerequisites

### 3.1 Accounts and access

- **Exotel** account with **Agent Stream** / Voicebot applet enabled
- **Sarvam AI** API key — [Sarvam dashboard](https://www.sarvam.ai)
- **OpenAI** (or other LLM) API key for the reasoning layer
- **Public WSS endpoint** (TLS recommended): e.g. `wss://your-host:5060/media?sample-rate=8000`

### 3.2 Runtime

| Stack | Minimum |
|-------|---------|
| **Node.js** (reference bot) | 18+, `npm ci` |
| **Python** (this repo) | 3.8+, `pip install -r requirements.txt` |

### 3.3 Network

- Outbound HTTPS to `api.sarvam.ai`, `api.openai.com`
- Inbound WSS from Exotel (allowlist Exotel egress if using firewall rules)
- Timeouts: STT 10–12 s, TTS 15 s, LLM per provider defaults

---

## 4. Connectivity modes

### 4.1 PSTN / SIP (phone)

```
Caller → PSTN → Exotel SIP → Agent Stream (WSS) → Voice bot
```

**Use cases:** Support hotlines, outbound campaigns, IVR replacement.

### 4.2 WSS / WebRTC (browser)

```
Caller → Browser WebRTC → Agent Stream (WSS) → Voice bot
```

**Use cases:** Demos, in-app assistants, internal tools.

**Production note:** Configure the **same bot URL** in Exotel for both flows. Load-test each path separately—jitter and codec artifacts differ from PSTN.

---

## 5. Voice pipeline

### 5.1 Per-turn sequence

1. Buffer `media` frames while caller speaks.
2. Detect end-of-turn (silence + minimum speech duration).
3. **STT** — Sarvam `saaras:v3`, `language_code: unknown`.
4. **LLM** — short replies (60–120 `max_tokens` for voice).
5. **TTS** — Sarvam `bulbul:v3`, speaker e.g. `shubh`, auto `hi-IN` / `en-IN`.
6. **Playback** — real-time 20 ms pacing + `mark` for completion.
7. On interrupt → `clear` + cancel in-flight pipeline (epoch/turn id).

### 5.2 Latency budget

| Stage | Service | Model | Typical |
|-------|---------|-------|---------|
| STT | Sarvam | `saaras:v3` | 800–1200 ms |
| LLM | OpenAI | `gpt-4o-mini` | 300–600 ms |
| TTS | Sarvam | `bulbul:v3` | 400–800 ms |
| **Total** | | | **1.5–2.5 s** |

### 5.3 Turn-detection defaults (telephony-tuned)

```javascript
const PIPELINE_LATENCY_DEFAULTS = {
  silenceLevelThreshold: 50,  // amplitude below = silence
  silenceThreshold: 8,      // 8 × 20 ms = 160 ms silence
  minAudioChunks: 15,         // ~300 ms minimum speech
  processingCooldown: 600,    // ms between turns
};
```

Strip silent chunks before STT to improve accuracy on noisy PSTN lines.

---

## 6. Exotel Agent Stream protocol

| Event | Direction | Description |
|-------|-----------|-------------|
| `connected` | Server → Bot | WSS established |
| `start` | Server → Bot | `call_sid`, `from`, `to`, `sample_rate` |
| `media` | Bidirectional | Base64 16-bit PCM, typically 320 B / frame |
| `mark` | Bidirectional | Playback position |
| `clear` | Bot → Server | Stop playback (barge-in) |
| `stop` | Server → Bot | Call ended |

**Stream URL example:**

```text
wss://your-server.example.com/media?sample-rate=8000
```

---

## 7. Sarvam API integration

### 7.1 Speech-to-text

**Endpoint:** `POST https://api.sarvam.ai/speech-to-text`  
**Auth header:** `api-subscription-key: <SARVAM_API_KEY>`

| Field | Value |
|-------|--------|
| `model` | `saaras:v3` |
| `mode` | `transcribe` |
| `language_code` | `unknown` (auto-detect) |
| `file` | WAV, 16 kHz mono recommended |

**Node.js (production pattern):**

```javascript
async function transcribeAudio(pcmBuffer, sampleRate, apiKey) {
  const pcm16k = resample(pcmBuffer, sampleRate, 16000);
  const wavBuffer = createWavBuffer(pcm16k, 16000);

  if (pcm16k.length / (16000 * 2) < 0.55) {
    return { text: '', rateLimited: false };
  }

  const form = new FormData();
  form.append('model', 'saaras:v3');
  form.append('mode', 'transcribe');
  form.append('language_code', 'unknown');
  form.append('file', new Blob([wavBuffer], { type: 'audio/wav' }), 'audio.wav');

  const resp = await fetch('https://api.sarvam.ai/speech-to-text', {
    method: 'POST',
    headers: { 'api-subscription-key': apiKey },
    body: form,
    signal: AbortSignal.timeout(12000),
  });

  if (resp.status === 429) return { text: '', rateLimited: true };
  if (!resp.ok) return { text: '', rateLimited: false };

  const data = await resp.json();
  return { text: (data.transcript || '').trim(), rateLimited: false };
}
```

**Python:**

```python
import requests
from audio_utils import resample, create_wav

def transcribe_audio(pcm_buffer: bytes, sample_rate: int = 8000, api_key: str) -> str:
    if sample_rate != 16000:
        pcm_buffer = resample(pcm_buffer, sample_rate, 16000)
    wav_buffer = create_wav(pcm_buffer, 16000)
    if len(pcm_buffer) / (16000 * 2) < 0.55:
        return ""

    response = requests.post(
        "https://api.sarvam.ai/speech-to-text",
        headers={"api-subscription-key": api_key},
        files={"file": ("audio.wav", wav_buffer, "audio/wav")},
        data={"model": "saaras:v3", "mode": "transcribe", "language_code": "unknown"},
        timeout=12,
    )
    response.raise_for_status()
    return response.json().get("transcript", "").strip()
```

### 7.2 Text-to-speech

**Endpoint:** `POST https://api.sarvam.ai/text-to-speech`

```javascript
async function synthesizeSpeech(text, languageCode, apiKey) {
  const resp = await fetch('https://api.sarvam.ai/text-to-speech', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-subscription-key': apiKey,
    },
    body: JSON.stringify({
      text,
      target_language_code: languageCode || 'en-IN',
      speaker: 'shubh',
      model: 'bulbul:v3',
      speech_sample_rate: '24000',
      output_audio_codec: 'linear16',
      pace: 1.0,
    }),
    signal: AbortSignal.timeout(15000),
  });

  const data = await resp.json();
  const raw = Buffer.from(data.audios[0], 'base64');
  const pcm24 = raw.slice(0, 4).toString('ascii') === 'RIFF' ? wavToPcm(raw) : raw;
  return resample(pcm24, 24000, 8000);
}
```

**Language selection:**

```javascript
function ttsLanguageForText(text) {
  const ascii = (text.match(/[\x00-\x7F]/g) || []).length;
  return ascii / Math.max(text.length, 1) > 0.85 ? 'en-IN' : 'hi-IN';
}
```

### 7.3 Supported languages

| Language | Code |
|----------|------|
| Hindi | `hi-IN` |
| English (India) | `en-IN` |
| Tamil | `ta-IN` |
| Telugu | `te-IN` |
| Kannada | `kn-IN` |
| Malayalam | `ml-IN` |
| Bengali | `bn-IN` |
| Marathi | `mr-IN` |
| Gujarati | `gu-IN` |
| Punjabi | `pa-IN` |

Use `language_code: unknown` in STT for automatic detection and Hindi–English code-switching.

---

## 8. Reference implementations

### 8.1 Node.js (recommended for Agent Stream WSS)

Full reference bot pattern:

- WebSocket server on port **5060**
- Pre-cached greeting via Sarvam TTS at startup
- Barge-in via `sendClear()` + pipeline epoch
- Whisper fallback on Sarvam HTTP 429 (15 s backoff)

Example layout (Exotel voice-bot monorepos):

```text
examples/sarvam-bot.js          # Main entry
src/core/server.js            # Exotel WSS handler
src/core/utils/botUtils.js      # Turn detect, pacing, WAV helpers
```

**Quick start:**

```bash
export SARVAM_API_KEY=...
export OPENAI_API_KEY=...
export PORT=5060
node examples/sarvam-bot.js
```

Health check: `GET http://localhost:5060/health` → `200`.

### 8.2 Python (this repository)

This repo provides a **Python bot framework** with pluggable STT/TTS engines. Extend `engines/stt_engine.py` and `engines/tts_engine.py` with Sarvam providers using the API patterns in [§7](#7-sarvam-api-integration).

```bash
git clone https://github.com/exotel/Agent-Stream.git
cd Agent-Stream
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Set SARVAM_API_KEY, OPENAI_API_KEY
python main.py
```

See [`examples/sarvam_agentstream_pipeline.py`](examples/sarvam_agentstream_pipeline.py) for minimal Sarvam STT/TTS helpers aligned with this guide.

---

## 9. Production engineering

### 9.1 Real-time audio pacing

Do **not** send all TTS bytes in one burst. Telephony gateways expect **320 bytes every 20 ms**.

```javascript
async function sendAudioRealtimePaced(sender, audioBuffer) {
  const frameBytes = 320;
  const burstFrames = 8;
  let frameIndex = 0;
  for (let i = 0; i < audioBuffer.length; i += frameBytes) {
    sender.sendMedia(audioBuffer.slice(i, i + frameBytes));
    frameIndex++;
    if (frameIndex >= burstFrames) await sleep(20);
  }
}
```

### 9.2 Barge-in (epoch-based turns)

1. Detect speech while `isBotSpeaking`.
2. `sender.sendClear()`.
3. Increment turn epoch; discard stale STT/LLM/TTS results.

```javascript
if (!isCurrentTurn(session, epoch)) return; // discard stale pipeline output
```

### 9.3 Rate-limit resilience

On Sarvam STT **HTTP 429**:

- Set `sttBackoffUntil = now + 15000`.
- Fall back to **OpenAI Whisper** for that turn.
- Resume Sarvam after backoff.

Callers should not hear hard failures—only slightly different STT latency.

### 9.4 Pre-cached greeting

Generate greeting TTS at **process startup**, not on first `start` event.

```javascript
const GREETING = 'Namaste! Main aapki kaise madad kar sakta hoon?';
cachedGreeting = await synthesizeSpeech(GREETING, 'hi-IN');
```

### 9.5 Empty STT handling

If transcript length &lt; 2 characters:

- Log and optionally play a short reprompt TTS.
- Do not call LLM with empty input.

### 9.6 LLM voice constraints

```javascript
{
  role: 'system',
  content:
    'You are a voice assistant on a phone call. Reply in 1-2 short sentences. ' +
    'Match the user language (Hindi, English, or mixed). Be conversational.',
}
max_tokens: 90,
```

---

## 10. Exotel configuration

1. Create / configure **Voicebot** or **Agent Stream** applet.
2. Set **Stream URL** to your public WSS endpoint.
3. Enable **bidirectional** streaming and **8 kHz** sample rate query param.
4. Set **StatusCallback** URL if you need CDR/recording enrichment.
5. For outbound: `Calls/connect` with `StreamUrl` pointing to the same bot.

**Outbound example (conceptual):**

```http
POST /v1/Accounts/{sid}/Calls/connect.json
StreamUrl=wss://your-host/media?sample-rate=8000
StreamType=bidirectional
```

---

## 11. Deployment

### 11.1 Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SARVAM_API_KEY` | Yes | Sarvam subscription key |
| `OPENAI_API_KEY` | Yes | LLM (and Whisper fallback) |
| `PORT` | No | Default `5060` |
| `BOOTH_DEMO_URL` | No | Optional event webhook for ops UI |
| `LOG_LEVEL` | No | `info` / `debug` |

### 11.2 Docker (Node reference)

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 5060
HEALTHCHECK CMD wget -qO- http://127.0.0.1:5060/health || exit 1
CMD ["node", "examples/sarvam-bot.js"]
```

### 11.3 Process supervision

- Run behind **reverse proxy** with TLS termination (`wss://`).
- **Restart policy:** `unless-stopped`.
- **Single worker per stream** — one Node process handles many concurrent WSS connections; load-test your target CPS.

### 11.4 Production checklist

- [ ] TLS on public WSS URL
- [ ] Secrets in env / secret manager (never in git)
- [ ] Health check wired to load balancer
- [ ] STT/TTS timeouts configured
- [ ] Whisper fallback tested under 429 simulation
- [ ] Barge-in tested on real PSTN line
- [ ] Sample-rate path verified with oscilloscope or recording analysis
- [ ] Exotel `start` / `stop` events logged with `call_sid`
- [ ] Rate limits understood for Sarvam plan tier

---

## 12. Observability

Log per turn (structured JSON recommended):

```json
{
  "call_sid": "…",
  "stt_ms": 920,
  "llm_ms": 410,
  "tts_ms": 680,
  "total_ms": 2010,
  "stt_provider": "sarvam",
  "language_detected": "hi-IN",
  "barge_in": false
}
```

**Alert on:**

- STT error rate &gt; 5% over 5 min
- p95 turn latency &gt; 4 s
- Sarvam 429 rate (consider plan upgrade)
- WSS disconnect spike

---

## 13. Performance targets

| Metric | Target |
|--------|--------|
| Average turn latency | ~1.8 s |
| STT accuracy (Hindi, telephony) | ~92% |
| STT accuracy (English, telephony) | ~95% |
| Barge-in stop playback | &lt; 100 ms |
| Cached greeting playback | &lt; 50 ms |

---

## 14. Troubleshooting runbook

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Greeting only, then silence | OpenAI/Sarvam not connected; audio dropped before `connected` | Buffer media until upstream ready; check API keys |
| Empty transcripts | Audio &lt; 0.55 s; wrong sample rate | Tune VAD; verify 8→16 kHz upsample |
| Robotic / chipmunk audio | Wrong resample (24↔8 kHz) | Trace TTS output path |
| Choppy playback | All audio sent at once | Use 20 ms pacing |
| HTTP 429 on STT | Sarvam rate limit | Whisper fallback + backoff |
| High latency | Long LLM/TTS | Lower `max_tokens`; shorten replies |
| Bot offline in UI | ngrok/tunnel wrong port | Tunnel **5060** for Sarvam |

---

## 15. Security checklist

- Rotate `SARVAM_API_KEY` and `OPENAI_API_KEY` on compromise.
- Do not log raw API keys or full audio payloads in production.
- Restrict WSS origin / IP if Exotel provides stable egress ranges.
- Use `NODE_TLS_REJECT_UNAUTHORIZED=1` in production (only disable for known staging MITM issues).

---

## 16. Roadmap

- Streaming STT (start LLM before caller finishes) — save 500–800 ms
- Streaming TTS — play before full synthesis completes
- Neural VAD (e.g. Silero) instead of amplitude-only detection
- Multi-turn persistence across transfers
- Native Sarvam engine modules in Python `engines/`

---

## 17. References

- [Exotel Agent Stream — branches & code](https://github.com/exotel/Agent-Stream)
- [Exotel Agent Stream API](https://developer.exotel.com/api/agent-stream)
- [Sarvam AI API documentation](https://docs.sarvam.ai)
- [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat)

---

**Maintainers:** Exotel Agent Stream team  
**Feedback:** Open an issue on [exotel/Agent-Stream](https://github.com/exotel/Agent-Stream/issues) with label `sarvam-integration`.
