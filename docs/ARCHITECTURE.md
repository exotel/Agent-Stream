# Architecture Documentation

## Overview

This document provides a comprehensive overview of the Exotel Voice AI Bot Framework architecture, including all components, data flows, and integration points.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 END USER                                        │
│                            (Phone Call / Mobile)                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ PSTN/VoIP Call
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXOTEL CLOUD                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  • Telephony Infrastructure (PSTN Gateway)                              │   │
│  │  • Call Routing & IVR                                                   │   │
│  │  • Media Streaming (WebSocket)                                          │   │
│  │  • Call Recording & Analytics                                           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ WebSocket (wss://)
                                       │ Protocol: Exotel Media Streaming
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VOICE BOT SERVER (This Repository)                     │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        WSS Server (src/core/server.js)                   │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐ │  │
│  │  │ Message Handler│  │ Message Sender │  │ Session Manager            │ │  │
│  │  │ (Decode audio) │  │ (Encode audio) │  │ (Track call state)         │ │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                       │                                         │
│                    ┌──────────────────┼──────────────────┐                     │
│                    │                  │                  │                     │
│                    ▼                  ▼                  ▼                     │
│  ┌────────────────────┐  ┌────────────────┐  ┌────────────────────────────┐   │
│  │   REALTIME BOTS    │  │  BRIDGE BOTS   │  │     PIPELINE BOTS          │   │
│  │   (WebSocket→AI)   │  │  (WebSocket→AI)│  │     (HTTP API→AI)          │   │
│  │                    │  │                │  │                            │   │
│  │ • openai-realtime  │  │ • elevenlabs   │  │ • speech-to-speech         │   │
│  │                    │  │ • gemini-live  │  │ • gemini-bot               │   │
│  │                    │  │                │  │ • simple-chat              │   │
│  └────────────────────┘  └────────────────┘  └────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                           Shared Utilities                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │ AudioResampler│ │   BotUtils   │  │    Logger    │  │HealthCheck │  │  │
│  │  │ (8k↔16k↔24k) │  │ (State mgmt) │  │ (Structured) │  │ (Monitoring)│  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
│   OPENAI CLOUD    │      │  ELEVENLABS CLOUD │      │   GOOGLE CLOUD    │
│                   │      │                   │      │                   │
│ • Realtime API    │      │ • Conversational  │      │ • Gemini API      │
│ • Whisper (STT)   │      │   AI Agents       │      │ • Gemini Live     │
│ • GPT-4 (LLM)     │      │ • Voice Synthesis │      │                   │
│ • TTS             │      │                   │      │                   │
└───────────────────┘      └───────────────────┘      └───────────────────┘
```

---

## Component Details

### 1. Exotel Cloud

Exotel provides the telephony infrastructure that connects phone calls to our bot server.

#### Exotel Components

| Component | Description |
|-----------|-------------|
| **PSTN Gateway** | Connects traditional phone networks to VoIP |
| **Virtual Numbers** | Inbound phone numbers (e.g., +91YYYYYYYYYY) |
| **ExoML Flows** | Visual IVR builder that routes calls |
| **Stream Applet** | WebSocket streaming for real-time audio |
| **Call API** | REST API to initiate outbound calls |

#### Exotel WebSocket Protocol

```
Exotel → Bot Server (Incoming Events)
├── start      - Call initiated, contains metadata
├── media      - Audio chunk (base64 encoded PCM)
├── mark       - Playback marker reached
├── clear      - Stop current playback (barge-in)
└── stop       - Call ended

Bot Server → Exotel (Outgoing Events)
├── media      - Audio to play (base64 encoded PCM)
├── mark       - Set playback marker
└── clear      - Request to stop playback
```

#### Audio Format (Exotel)

| Property | Value |
|----------|-------|
| Format | PCM (Linear16) |
| Sample Rate | 8000 Hz |
| Bit Depth | 16-bit |
| Channels | Mono |
| Chunk Size | 3200 bytes (200ms) minimum |

---

### 2. Voice Bot Server (This Repository)

The core server that bridges Exotel with AI providers.

#### Directory Structure

```
src/
├── core/
│   ├── server.js           # WebSocket server (receives Exotel connections)
│   ├── config.js           # Configuration management
│   ├── handlers/
│   │   ├── messageHandler.js   # Decode incoming Exotel messages
│   │   └── messageSender.js    # Encode outgoing messages to Exotel
│   ├── utils/
│   │   ├── audioResampler.js   # Convert between sample rates
│   │   ├── botUtils.js         # Shared bot utilities
│   │   ├── logger.js           # Structured logging
│   │   └── exotelApi.js        # Exotel REST API client
│   └── audio/
│       └── audioProcessor.js   # Audio processing utilities
│
├── bots/                   # Organized bot implementations
│   ├── realtime/           # WebSocket-based (lowest latency)
│   ├── conversational/     # All-in-one AI agents
│   ├── pipeline/           # STT → LLM → TTS
│   └── experimental/       # Beta features
│
└── examples/               # Working bot implementations
    ├── openai-realtime-bot.js
    ├── elevenlabs-bridge.js
    ├── speech-to-speech-bot.js
    ├── gemini-speech-to-speech-bot.js
    └── simple-conversation-bot.js
```

#### Core Components

##### WSS Server (`src/core/server.js`)

```javascript
// Responsibilities:
// 1. Accept WebSocket connections from Exotel
// 2. Route messages to appropriate handlers
// 3. Manage session lifecycle
// 4. Handle connection health (ping/pong)

createServer({
  port: 5001,
  path: '/media',
  onStart: (session, sender) => { /* Call started */ },
  onMedia: (session, sender, audioBuffer) => { /* Audio received */ },
  onMark: (session, sender, markName) => { /* Playback marker */ },
  onStop: (session) => { /* Call ended */ }
});
```

##### Message Handler (`src/core/handlers/messageHandler.js`)

```javascript
// Responsibilities:
// 1. Parse incoming Exotel JSON messages
// 2. Decode base64 audio to PCM buffer
// 3. Extract metadata (streamId, callerId, etc.)
// 4. Dispatch to appropriate callbacks
```

##### Message Sender (`src/core/handlers/messageSender.js`)

```javascript
// Responsibilities:
// 1. Encode PCM audio to base64
// 2. Format messages according to Exotel protocol
// 3. Validate chunk sizes (3200 bytes minimum)
// 4. Send media, mark, and clear events
```

##### Audio Resampler (`src/core/utils/audioResampler.js`)

```javascript
// Responsibilities:
// 1. Convert 8kHz (Exotel) ↔ 16kHz (Whisper) ↔ 24kHz (OpenAI TTS)
// 2. Linear interpolation for upsampling
// 3. Averaging for downsampling
// 4. Preserve audio quality during conversion

resample(buffer, fromRate, toRate);
to8kHz(buffer, fromRate);   // For sending to Exotel
to16kHz(buffer, fromRate);  // For Whisper STT
to24kHz(buffer, fromRate);  // For OpenAI Realtime
```

##### BotUtils (`src/core/utils/botUtils.js`)

```javascript
// Shared utilities for all bots:
// 1. SessionState - Track conversation state
// 2. AudioUtils - Audio processing helpers
// 3. BargeInHandler - Handle user interruptions
// 4. EXOTEL_CONSTANTS - Standard values

EXOTEL_CONSTANTS = {
  SAMPLE_RATE: 8000,
  BITS_PER_SAMPLE: 16,
  MIN_CHUNK_SIZE: 3200,    // 200ms
  BYTES_PER_CHUNK: 320,    // 20ms
  SILENCE_THRESHOLD: 300
};
```

---

### 3. Bot Architectures

#### 3.1 Realtime Bots (WebSocket → AI)

**Lowest latency (~500ms)**

```
┌──────────┐      ┌──────────────┐      ┌──────────────┐
│  Exotel  │ WSS  │  Our Server  │ WSS  │ OpenAI       │
│  (8kHz)  │ ───► │  (resample)  │ ───► │ Realtime API │
│          │ ◄─── │  (24kHz↔8k)  │ ◄─── │ (24kHz)      │
└──────────┘      └──────────────┘      └──────────────┘
```

**OpenAI Realtime Bot (`openai-realtime-bot.js`)**

| Component | Details |
|-----------|---------|
| Protocol | WebSocket (`wss://api.openai.com/v1/realtime`) |
| Model | `gpt-4o-realtime-preview` |
| Audio In | 24kHz PCM (we upsample from 8kHz) |
| Audio Out | 24kHz PCM (we downsample to 8kHz) |
| Features | Native speech-to-speech, function calling |

```javascript
// Connection flow:
1. Exotel connects to our server
2. We connect to OpenAI Realtime API
3. Audio flows bidirectionally:
   Exotel (8k) → Resample (24k) → OpenAI
   OpenAI (24k) → Resample (8k) → Exotel
```

#### 3.2 Bridge Bots (WebSocket → AI Agent)

**Best voice quality (~750ms)**

```
┌──────────┐      ┌──────────────┐      ┌──────────────┐
│  Exotel  │ WSS  │  Our Server  │ WSS  │ ElevenLabs   │
│  (8kHz)  │ ───► │  (bridge)    │ ───► │ Conv. AI     │
│          │ ◄─── │  (16kHz↔8k)  │ ◄─── │ (16kHz)      │
└──────────┘      └──────────────┘      └──────────────┘
```

**ElevenLabs Bridge (`elevenlabs-bridge.js`)**

| Component | Details |
|-----------|---------|
| Protocol | WebSocket (`wss://api.elevenlabs.io/v1/convai/conversation`) |
| Agent | Configured in ElevenLabs Dashboard |
| Audio In | 16kHz PCM |
| Audio Out | 16kHz PCM (MP3 chunks from ElevenLabs) |
| Features | Custom agents, knowledge base, voice cloning |

```javascript
// Event mapping:
Exotel start      → ElevenLabs conversation_initiation_client_data
Exotel media      → ElevenLabs user_audio_chunk
ElevenLabs audio  → Exotel media
ElevenLabs interrupt → Exotel clear
```

**Gemini Live Bridge (`gemini-live-bridge.js`)**

| Component | Details |
|-----------|---------|
| Protocol | WebSocket (`wss://generativelanguage.googleapis.com/ws/...`) |
| Model | `gemini-2.0-flash-exp` |
| Status | Beta (requires special API access) |

#### 3.3 Pipeline Bots (HTTP API → AI)

**Most flexible (~4s latency)**

```
┌──────────┐      ┌──────────────────────────────────────────────┐
│  Exotel  │      │                 Our Server                   │
│  (8kHz)  │      │  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│          │ ───► │  │   STT   │→ │   LLM   │→ │    TTS      │  │
│          │ ◄─── │  │ (Whisper│  │ (GPT-4) │  │ (OpenAI TTS)│  │
└──────────┘      │  └─────────┘  └─────────┘  └─────────────┘  │
                  └──────────────────────────────────────────────┘
                         │              │              │
                         ▼              ▼              ▼
                  ┌─────────────────────────────────────────────┐
                  │              OpenAI HTTP APIs               │
                  │  /v1/audio/transcriptions  (Whisper)        │
                  │  /v1/chat/completions      (GPT-4)          │
                  │  /v1/audio/speech          (TTS)            │
                  └─────────────────────────────────────────────┘
```

**Speech-to-Speech Bot (`speech-to-speech-bot.js`)**

| Stage | API | Latency |
|-------|-----|---------|
| STT | OpenAI Whisper | ~1s |
| LLM | OpenAI GPT-4 | ~1.5s |
| TTS | OpenAI TTS | ~1.5s |
| **Total** | | **~4s** |

**Gemini Bot (`gemini-speech-to-speech-bot.js`)**

| Stage | API | Latency |
|-------|-----|---------|
| STT+LLM | Gemini 2.5 Flash (audio input) | ~2.5s |
| TTS | OpenAI TTS | ~1.5s |
| **Total** | | **~4s** |

---

### 4. AI Provider Details

#### 4.1 OpenAI

| Service | Endpoint | Use Case |
|---------|----------|----------|
| **Realtime API** | `wss://api.openai.com/v1/realtime` | True speech-to-speech |
| **Whisper** | `POST /v1/audio/transcriptions` | Speech-to-text |
| **GPT-4** | `POST /v1/chat/completions` | Text generation |
| **TTS** | `POST /v1/audio/speech` | Text-to-speech |

**Voices Available**: `alloy`, `nova`, `shimmer`, `echo`, `onyx`, `fable`

#### 4.2 ElevenLabs

| Service | Endpoint | Use Case |
|---------|----------|----------|
| **Conversational AI** | `wss://api.elevenlabs.io/v1/convai/conversation` | All-in-one voice agent |
| **Speech Synthesis** | `POST /v1/text-to-speech/{voice_id}` | High-quality TTS |

**Features**: 
- Custom agent personas
- Knowledge base integration
- Voice cloning
- Multi-language support

#### 4.3 Google Gemini

| Service | Endpoint | Use Case |
|---------|----------|----------|
| **Gemini API** | `POST /v1beta/models/gemini-2.5-flash:generateContent` | Text + audio understanding |
| **Gemini Live** | `wss://generativelanguage.googleapis.com/ws/...` | Real-time conversation (beta) |

---

### 5. Data Flow Examples

#### 5.1 Incoming Call Flow

```
1. User dials Exotel number (+91YYYYYYYYYY)
2. Exotel routes to configured flow (ExoML)
3. Flow triggers Stream applet with WSS URL
4. Exotel connects to our server: wss://our-server/media
5. Exotel sends 'start' event with metadata:
   {
     "event": "start",
     "start": {
       "streamId": "abc123",
       "callId": "call_xyz",
       "from": "+91XXXXXXXXXX",
       "to": "+91YYYYYYYYYY",
       "customParameters": { ... }
     }
   }
6. Our server initializes session and connects to AI
7. Bot sends greeting audio
8. Conversation begins...
```

#### 5.2 Audio Processing Flow (Pipeline Bot)

```
1. Exotel sends media event:
   { "event": "media", "media": { "payload": "base64..." } }

2. MessageHandler decodes:
   base64 → Buffer (PCM 8kHz)

3. Bot accumulates audio chunks (~800ms)

4. Silence detected → Process speech:
   a. Resample: 8kHz → 16kHz
   b. Create WAV buffer
   c. Send to Whisper STT
   d. Get transcription text

5. Send to LLM (GPT-4):
   a. Add to conversation history
   b. Get AI response text

6. Send to TTS (OpenAI):
   a. Generate speech audio (24kHz)
   b. Resample: 24kHz → 8kHz

7. Send to Exotel:
   a. Chunk into 3200-byte segments
   b. Encode as base64
   c. Send media events
   d. Send mark event at end
```

#### 5.3 Barge-in (Interruption) Flow

```
1. Bot is speaking (sending audio to Exotel)
2. User starts talking
3. Exotel detects voice activity
4. Exotel sends 'clear' event (or audio with high level)
5. Our server:
   a. Stops sending audio
   b. Sets isBotSpeaking = false
   c. Clears pending audio buffer
   d. (For bridge bots) Sends interruption to AI
6. Processes new user input
```

---

### 6. Latency Optimization

#### 6.1 Strategies Implemented

| Strategy | Implementation | Improvement |
|----------|----------------|-------------|
| **Pre-cached Greeting** | Generate TTS at startup | -2s first response |
| **Parallel Connection** | Connect to AI during greeting | -1s |
| **Small Chunks** | 640 bytes for ElevenLabs | Better barge-in |
| **Early Media** | Send before full processing | -200ms perceived |
| **Session Reuse** | Keep AI connections alive | -500ms |

#### 6.2 Latency Breakdown

```
Pipeline Bot (worst case):
├── Audio accumulation:    800ms
├── Silence detection:     200ms
├── Whisper STT:          1000ms
├── GPT-4 LLM:            1500ms
├── OpenAI TTS:           1500ms
└── Audio transmission:    100ms
    ─────────────────────────────
    Total:                ~5100ms

Realtime Bot (best case):
├── Audio transmission:    50ms
├── OpenAI processing:    400ms
└── Audio return:          50ms
    ─────────────────────────────
    Total:                 ~500ms
```

---

### 7. Deployment Architecture

#### 7.1 Single Server Deployment

```
┌─────────────────────────────────────────────────────┐
│                   Docker Host                       │
│  ┌───────────────────────────────────────────────┐ │
│  │           voice-bot Container                 │ │
│  │                                               │ │
│  │  Node.js App (:5001)                         │ │
│  │    └── WebSocket Server                      │ │
│  │                                               │ │
│  └───────────────────────────────────────────────┘ │
│                        │                            │
│                   Port 5001                         │
└────────────────────────┼────────────────────────────┘
                         │
                    Nginx/Traefik
                    (SSL Termination)
                         │
                    Public URL
              wss://bot.example.com/media
```

#### 7.2 Production Deployment (Recommended)

```
                        Internet
                            │
                    ┌───────┴───────┐
                    │  Load Balancer │
                    │  (SSL/TLS)     │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Bot Pod 1│     │ Bot Pod 2│     │ Bot Pod 3│
    │ (5001)   │     │ (5001)   │     │ (5001)   │
    └──────────┘     └──────────┘     └──────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                    ┌───────┴───────┐
                    │    Redis      │
                    │ (Session Sync)│
                    └───────────────┘
```

---

### 8. Security Considerations

| Layer | Protection |
|-------|------------|
| **Transport** | TLS 1.3 (wss://) |
| **Authentication** | API keys in environment variables |
| **Authorization** | Exotel IP whitelisting (optional) |
| **Data** | No call recording by default |
| **Secrets** | .env file (gitignored) |

---

### 9. Monitoring & Observability

#### Logging

```javascript
// Structured logging with correlation IDs
logger.info('Processing audio', {
  streamId: session.streamId,
  audioLength: buffer.length,
  processingTime: Date.now() - startTime
});
```

#### Health Checks

```
GET /health
{
  "status": "healthy",
  "checks": {
    "server": "up",
    "memory": { "used": "150MB", "total": "512MB" },
    "uptime": "2h 30m"
  }
}
```

#### Metrics to Track

| Metric | Description |
|--------|-------------|
| `call_count` | Total calls handled |
| `call_duration_avg` | Average call length |
| `latency_first_response` | Time to first bot speech |
| `latency_round_trip` | User speech → Bot response |
| `error_rate` | Failed calls percentage |

---

## Quick Reference

### Bot Selection Guide

| Requirement | Recommended Bot |
|-------------|-----------------|
| Lowest latency | `openai-realtime-bot` |
| Best voice quality | `elevenlabs-bridge` |
| Custom AI logic | `speech-to-speech-bot` |
| Google AI ecosystem | `gemini-speech-to-speech-bot` |
| Simple prototype | `simple-conversation-bot` |

### Environment Variables

```bash
# Required for all bots
PORT=5001

# OpenAI bots
OPENAI_API_KEY=sk-...

# ElevenLabs bot
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...

# Gemini bot
GEMINI_API_KEY=AIza...

# Exotel API (outbound calls)
EXOTEL_API_KEY=...
EXOTEL_API_TOKEN=...
EXOTEL_ACCOUNT_SID=...
```

### Common Commands

```bash
# Run bots
npm run openai-realtime    # Fastest
npm run elevenlabs-bot     # Best quality
npm run gemini-bot         # Google AI
npm start                  # Simple chat

# Development
npm test                   # Run tests
npm run lint               # Check code style

# Deployment
docker-compose up -d       # Start with Docker
```

---

## Appendix

### A. Exotel WebSocket Message Examples

#### Start Event
```json
{
  "event": "start",
  "start": {
    "streamId": "stream_abc123",
    "callId": "call_xyz789",
    "from": "+919876543210",
    "to": "+91YYYYYYYYYY",
    "direction": "inbound",
    "customParameters": {
      "userId": "user_123",
      "campaign": "support"
    }
  }
}
```

#### Media Event
```json
{
  "event": "media",
  "media": {
    "payload": "base64EncodedPCMAudio...",
    "timestamp": 1234567890
  }
}
```

#### Outgoing Media
```json
{
  "event": "media",
  "streamId": "stream_abc123",
  "media": {
    "payload": "base64EncodedPCMAudio..."
  }
}
```

### B. Audio Format Conversion Table

| From | To | Method | Use Case |
|------|-----|--------|----------|
| 8kHz | 16kHz | Upsample 2x | Whisper STT |
| 8kHz | 24kHz | Upsample 3x | OpenAI Realtime |
| 16kHz | 8kHz | Downsample 2x | ElevenLabs → Exotel |
| 24kHz | 8kHz | Downsample 3x | OpenAI TTS → Exotel |

### C. Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `ECONNREFUSED` | AI service down | Retry with backoff |
| `401 Unauthorized` | Invalid API key | Check .env |
| `429 Rate Limited` | Too many requests | Implement queue |
| `WebSocket closed` | Connection dropped | Auto-reconnect |

---

*Last updated: December 2024*

