# Exotel AgentStream for Voice AI Framework 🤖

**Enterprise-grade Agent Stream for Voice AI framework for Exotel WebSocket streaming.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org)

```bash
npm install
cp .env.example .env    # Add your API keys
npm start               # Bot running!
```

---

## 🎯 Overview

This framework enables you to build AI-powered voice bots that work with Exotel's bidirectional WebSocket streaming. Choose from **7 production-ready bots**:

### 🏆 Available Bots

| Bot | Latency | Type | Best For | Command |
|-----|---------|------|----------|---------|
| **[OpenAI Realtime](#openai-realtime-bot)** | ~500ms ⚡ | WebSocket S2S | **Fastest production bot** | `npm run openai-realtime` |
| **[ElevenLabs Bridge](#elevenlabs-conversational-ai)** | ~750ms | WebSocket Agent | Best voice quality | `npm run elevenlabs-bot` |
| **[Gemini S2S](#gemini-speech-to-speech)** | ~2-4s | HTTP Pipeline | Google AI ecosystem | `npm run gemini-bot` |
| **[OpenAI Pipeline](#stt--llm--tts-pipeline)** | ~4s | HTTP Pipeline | Custom AI logic | `npm run s2s-bot` |
| **[Simple Chat](#simple-conversation-bot)** | ~4s | HTTP Pipeline | Quick prototyping | `npm start` |
| **Gemini Live** | ~600ms* | WebSocket S2S | Beta (needs access) | `npm run gemini-live` |
| **Gemini + ElevenLabs** | ~3s | Hybrid | Experimental | `npm run gemini-eleven` |

*\* Requires special API access*

### Architecture Comparison

| Architecture | How It Works | Pros | Cons |
|--------------|--------------|------|------|
| **Realtime (WebSocket)** | Direct speech-to-speech | Lowest latency, natural | Less customizable |
| **Bridge (WebSocket)** | All-in-one AI agent | Best quality, easy setup | Vendor-specific |
| **Pipeline (HTTP)** | STT → LLM → TTS chain | Full control, flexible | Higher latency |

---

## ✨ Features

- ✅ **Multiple AI Providers** - OpenAI, Gemini, ElevenLabs, Deepgram
- ✅ **Low Latency** - Optimized audio streaming with 20ms buffering
- ✅ **Barge-in Support** - Users can interrupt the bot mid-sentence
- ✅ **Audio Resampling** - Automatic 8kHz ↔ 16kHz conversion
- ✅ **Noise Cancellation** - RNNoise and Spectral processing
- ✅ **Production Ready** - Docker, health checks, structured logging
- ✅ **Enterprise Patterns** - Retry logic, circuit breaker, correlation IDs

---

## 🚀 Quick Start

### Installation

```bash
git clone <repository>
cd exotel-voice-bot
npm install
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# For ElevenLabs Bridge (recommended)
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_AGENT_ID=your-agent-id

# For STT → LLM → TTS pipeline
OPENAI_API_KEY=sk-proj-your-key-here

# For Gemini bot
GEMINI_API_KEY=AIza-your-key-here
```

### Run a Bot

```bash
# Recommended (fastest)
npm run openai-realtime   # OpenAI Realtime (~500ms latency)
npm run elevenlabs-bot    # ElevenLabs Conversational AI (~750ms)

# Pipeline bots (more customizable)
npm start                 # Simple GPT-4 conversation
npm run gemini-bot        # Gemini + OpenAI TTS
npm run s2s-bot           # OpenAI full pipeline
```

---

## ⚡ OpenAI Realtime Bot

### The Fastest Option (~500ms latency)

The OpenAI Realtime bot uses **GPT-4o's native speech-to-speech** capability - no separate STT or TTS needed. Audio goes directly to OpenAI and comes back as speech.

```
┌──────────┐      ┌──────────────┐      ┌──────────────────────┐
│  Exotel  │ WSS  │  Our Server  │ WSS  │  OpenAI Realtime API │
│  (8kHz)  │ ───► │  (resample)  │ ───► │  gpt-4o-realtime     │
│          │ ◄─── │  (24kHz↔8k)  │ ◄─── │  (24kHz native S2S)  │
└──────────┘      └──────────────┘      └──────────────────────┘
```

### Setup

```bash
# Set your OpenAI API key
OPENAI_API_KEY=sk-proj-your-key-here

# Run the bot
npm run openai-realtime
```

### Features

- ✅ **True Speech-to-Speech** - No STT/TTS chain
- ✅ **~500ms Latency** - Fastest response time
- ✅ **Pre-cached Greeting** - Instant first response
- ✅ **Barge-in Support** - Natural interruptions
- ✅ **Function Calling** - Integrate with your APIs

### Configuration

Edit the instructions in `examples/openai-realtime-bot.js`:

```javascript
instructions: `You are a helpful customer service agent for Acme Corp.
Keep responses brief (1-2 sentences). Be friendly and professional.`
```

---

## 🎙️ ElevenLabs Conversational AI

### What is it?

ElevenLabs Conversational AI is an **all-in-one voice agent platform** that handles STT, LLM, and TTS in a single optimized pipeline. Instead of chaining three separate services, everything happens on ElevenLabs' infrastructure.

```
┌─────────────────────────────────────────────────────────────┐
│              ElevenLabs Conversational AI                    │
│                                                              │
│   Audio In ──→ [STT] ──→ [LLM Agent] ──→ [TTS] ──→ Audio Out │
│                                                              │
│   All handled by ElevenLabs - you just send/receive audio   │
└─────────────────────────────────────────────────────────────┘
```

### Advantages

| Feature | ElevenLabs Bridge | Traditional STT→LLM→TTS |
|---------|-------------------|-------------------------|
| **Latency** | ~750ms | 2-4 seconds |
| **Voice Quality** | Industry-leading | Good |
| **Setup Complexity** | Configure agent once | Manage 3 services |
| **Interruption Handling** | Built-in | Manual implementation |
| **Costs** | Single billing | 3 separate providers |
| **Maintenance** | Minimal | High |

### How It Works

```
1. 📞 Exotel connects → wss://your-server/media
2. 🔌 Bridge connects to ElevenLabs Agent
3. 🎤 Caller speaks → Audio resampled 8kHz→16kHz → ElevenLabs
4. 🤖 Agent processes (STT → LLM → TTS in ~750ms)
5. 🔊 Response audio → Resampled 16kHz→8kHz → Caller hears response
6. ⚡ If user interrupts → CLEAR sent → Agent stops immediately
```

### Setup

1. **Create an ElevenLabs Agent**
   - Go to: https://elevenlabs.io/app/conversational-ai
   - Create a new agent with your desired personality and voice
   - Copy the Agent ID

2. **Configure Environment**
   ```bash
   ELEVENLABS_API_KEY=your-api-key
   ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxx
   ```

3. **Run the Bridge**
   ```bash
   npm run elevenlabs-bot
   ```

4. **Configure Exotel Flow**
   - Add Voicebot Applet to your flow
   - Set WebSocket URL: `wss://your-server:5001/media`

### Custom Parameters

Pass parameters from Exotel to the ElevenLabs agent:

```
wss://your-server:5001/media?customer_name=John&intent=sales
```

Use in your ElevenLabs agent prompt:
```
You are speaking with {{customer_name}} about {{intent}}.
```

### Use Cases

| Use Case | Description |
|----------|-------------|
| **Outbound Sales** | AI agents making cold calls with natural conversation |
| **Customer Support** | 24/7 voice support with instant responses |
| **Appointment Booking** | Schedule meetings with voice interface |
| **Surveys & Feedback** | Collect customer feedback via phone |
| **Lead Qualification** | Pre-qualify leads before human handoff |
| **Order Status** | Customers check order status by phone |
| **Payment Reminders** | Automated payment collection calls |

---

## 🔧 STT → LLM → TTS Pipeline

For maximum customization, use the traditional pipeline architecture:

```
Exotel Audio → [STT] → Text → [LLM] → Response → [TTS] → Audio → Exotel
                ↓              ↓                  ↓
            Whisper         GPT-4            OpenAI TTS
            Deepgram        Gemini           ElevenLabs
            Google          Claude           Google
```

### Available Bots

| Bot | Command | Features |
|-----|---------|----------|
| **Simple Conversation** | `npm start` | GPT-4 + OpenAI Whisper + OpenAI TTS |
| **Speech-to-Speech** | `npm run s2s-bot` | + Noise cancellation + Better VAD |

### Configuration

```bash
# Provider selection
AI_STT_PROVIDER=whisper    # whisper, deepgram, google
AI_TTS_PROVIDER=openai     # openai, elevenlabs, google
LLM_PROVIDER=openai        # openai, gemini, anthropic

# API Keys
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
```

---

## 🌟 Gemini Speech-to-Speech

Google's Gemini 2.0 Flash offers native audio understanding and generation:

```bash
GEMINI_API_KEY=AIza-your-key
npm run gemini-bot
```

### Features
- Native audio input/output (no separate STT/TTS)
- Multimodal understanding
- Fast inference

---

## 📁 Project Structure

```
├── src/                         # Core framework
│   ├── server.js                # WebSocket server base class
│   ├── config.js                # Configuration
│   ├── handlers/                # Message handling
│   │   ├── messageHandler.js    # Incoming Exotel events
│   │   └── messageSender.js     # Outgoing to Exotel
│   ├── audio/                   # Audio processing
│   │   ├── noiseCancellation.js # Noise reduction
│   │   └── audioProcessor.js    # Processing pipeline
│   └── utils/                   # Utilities
│       ├── audioResampler.js    # 8kHz ↔ 16kHz conversion
│       ├── logger.js            # Logging
│       └── errors.js            # Error handling
│
├── examples/                    # Bot implementations
│   ├── simple-conversation-bot.js
│   ├── speech-to-speech-bot.js
│   ├── gemini-speech-to-speech-bot.js
│   └── elevenlabs-bridge.js     # ⭐ Recommended
│
├── config/                      # Service configurations
│   └── ai-services.config.js
│
├── docs/                        # Documentation
│   ├── openapi.yaml             # REST API spec
│   └── WEBSOCKET_PROTOCOL.md    # Exotel protocol docs
│
├── tests/                       # Test suites
└── package.json
```

---

## 🔌 Exotel Integration

### WebSocket Protocol

Exotel sends these events to your WebSocket server:

| Event | Description |
|-------|-------------|
| `connected` | WebSocket connection established |
| `start` | Call started, includes call metadata |
| `media` | Audio data (16-bit PCM 8kHz, base64) |
| `dtmf` | DTMF keypress from caller |
| `stop` | Call ended |
| `mark` | Audio playback confirmation |

Your server can send:

| Event | Description |
|-------|-------------|
| `media` | Audio to play to caller |
| `clear` | Stop playing pending audio (for barge-in) |
| `mark` | Track audio completion |

### Configure Exotel Flow

1. **Create a Flow** in Exotel Dashboard
2. **Add Voicebot Applet**
3. **Set WebSocket URL**: `wss://your-server:5001/media`
4. **Optional**: Add sample rate parameter: `?sample-rate=8000`

### Make a Test Call (API)

```bash
curl -X POST "https://API_KEY:API_TOKEN@api.exotel.com/v1/Accounts/ACCOUNT_SID/Calls/connect.json" \
  -d "From=PHONE_NUMBER" \
  -d "CallerId=YOUR_EXOTEL_NUMBER" \
  -d "Url=http://my.exotel.com/ACCOUNT_SID/exoml/start_voice/FLOW_ID"
```

---

## 🏥 Health & Monitoring

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Full health status |
| `GET /health/live` | Kubernetes liveness |
| `GET /health/ready` | Kubernetes readiness |
| `GET /connections` | Active WebSocket connections |

### Response Example

```json
{
  "status": "ok",
  "uptime": 3600,
  "connections": 5,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## 📞 Exotel API Integration

### Make Calls Programmatically

```bash
# Using CLI
npm run call +91XXXXXXXXXX

# Or directly
node scripts/make-call.js 9876543210
```

### Using in Code

```javascript
const ExotelApi = require('./src/utils/exotelApi');

const exotel = new ExotelApi({
  apiKey: process.env.EXOTEL_API_KEY,
  apiToken: process.env.EXOTEL_API_TOKEN,
  accountSid: process.env.EXOTEL_ACCOUNT_SID
});

// Make a call
const call = await exotel.makeCall({
  from: '9876543210',           // Customer phone
  to: '+91YYYYYYYYYY',            // Your Exotel number
  callerId: '+91YYYYYYYYYY',
  flowUrl: 'http://my.exotel.com/Exotel/exoml/start_voice/YOUR_FLOW_ID'
});

console.log('Call SID:', call.Sid);
```

### Environment Variables

```bash
EXOTEL_API_KEY=your_api_key
EXOTEL_API_TOKEN=your_api_token
EXOTEL_ACCOUNT_SID=Exotel
EXOTEL_SUBDOMAIN=api.exotel.com
EXOTEL_VIRTUAL_NUMBER=+91YYYYYYYYYY
EXOTEL_FLOW_ID=YOUR_FLOW_ID
```

---

## 🛠️ Developer Guide

### Project Structure

```
.
├── src/                    # Core framework
│   ├── server.js          # WebSocket server
│   ├── config.js          # Configuration
│   ├── handlers/          # Message handling
│   └── utils/             # Utilities (audio, logging, API)
├── examples/              # Bot implementations
│   ├── elevenlabs-bridge.js       # ElevenLabs (recommended)
│   ├── gemini-speech-to-speech-bot.js
│   ├── simple-conversation-bot.js
│   └── speech-to-speech-bot.js
├── scripts/               # CLI tools
│   └── make-call.js       # Make test calls
├── tests/                 # Test files
├── docs/                  # Documentation
└── config/                # AI service configs
```

### Creating a Custom Bot

```javascript
const ExotelWSSServer = require('./src/server');

class MyBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
  }

  getMessageCallbacks(streamId, sender) {
    return {
      onStart: (data) => {
        console.log('Call started:', data.from);
        sender.sendMedia(this.getGreetingAudio());
      },
      
      onMedia: (data) => {
        // Process incoming audio
        const audioBuffer = data.audioBuffer;
        // Your AI logic here
      },
      
      onStop: () => {
        console.log('Call ended');
        this.sessions.delete(streamId);
      }
    };
  }
}

new MyBot().start();
```

### Available NPM Scripts

| Script | Description |
|--------|-------------|
| `npm start` | Run simple conversation bot |
| `npm run elevenlabs-bot` | Run ElevenLabs bridge (recommended) |
| `npm run gemini-bot` | Run Gemini speech-to-speech |
| `npm run call <phone>` | Make test call via Exotel API |
| `npm test` | Run all tests |
| `npm run test:bots` | Test all bot implementations |
| `npm run lint` | Check code style |
| `npm run health` | Check bot health endpoint |
| `npm run docker:build` | Build Docker image |
| `npm run docker:run` | Start with Docker Compose |

### Event Flow

```
Exotel                    Your Bot                   AI Service
  │                          │                           │
  │──── connected ──────────→│                           │
  │                          │                           │
  │──── start ──────────────→│                           │
  │                          │── Connect ───────────────→│
  │←─── media (greeting) ────│←── Audio ─────────────────│
  │                          │                           │
  │──── media (user audio) ─→│── Forward ───────────────→│
  │                          │                           │
  │←─── clear ───────────────│ (on user interrupt)       │
  │                          │                           │
  │←─── media (response) ────│←── Response ──────────────│
  │←─── mark ────────────────│ (track playback)          │
  │                          │                           │
  │──── stop ───────────────→│                           │
  │                          │── Disconnect ────────────→│
```

### Key Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `connected` | Exotel → Bot | WebSocket established |
| `start` | Exotel → Bot | Call begins, contains metadata |
| `media` | Both | Audio data (base64 PCM) |
| `clear` | Bot → Exotel | Stop current audio (barge-in) |
| `mark` | Both | Track audio playback position |
| `stop` | Exotel → Bot | Call ended |

### Audio Format

| Property | Value |
|----------|-------|
| Encoding | Base64 |
| Format | 16-bit PCM little-endian |
| Sample Rate | 8000 Hz |
| Channels | Mono |
| Chunk Size | 320 bytes (20ms) minimum |

---

## 🐳 Docker

### Quick Start

```bash
docker-compose up -d
```

### Build & Run

```bash
docker build -t exotel-voice-bot .
docker run -p 5001:5001 --env-file .env exotel-voice-bot
```

---

## 🧪 Testing

```bash
# Run all tests
npm test

# Test all bots
npm run test:bots

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage
```

---

## 📊 Performance Tuning

### Latency Optimization

| Setting | Default | Low Latency |
|---------|---------|-------------|
| Audio buffer | 3200 bytes (100ms) | 640 bytes (20ms) |
| Chunk alignment | 320 bytes | 320 bytes |

### Audio Quality

| Sample Rate | Quality | Bandwidth |
|-------------|---------|-----------|
| 8kHz | Standard (PSTN) | Low |
| 16kHz | Enhanced | Medium |
| 24kHz | HD | High |

---

## 🔐 Security

- API keys stored in environment variables
- WebSocket authentication support
- Non-root Docker user
- No sensitive data in logs

---

## 📚 Resources

### Documentation
- **[Architecture Guide](docs/ARCHITECTURE.md)** - Comprehensive system architecture & data flows
- **[Developer Quickstart](docs/DEVELOPER_QUICKSTART.md)** - Get running in 5 minutes
- **[Use Case Configuration](docs/guides/USE_CASE_CONFIGURATION.md)** - Configure bots for your business
- **[Best Practices](docs/guides/BEST_PRACTICES.md)** - Low-latency optimization guide
- [AI Bot Issues & Mitigations](docs/troubleshooting/AI_BOT_ISSUES_AND_MITIGATIONS.md) - Comprehensive guide on LLM issues and fixes
- [Exotel Integration Issues](docs/troubleshooting/EXOTEL_INTEGRATION_ISSUES.md) - Common Exotel integration problems and solutions
- [Event Flow & Latency](docs/guides/LATENCY_OPTIMIZATION.md) - End-to-end latency analysis and optimization
- [WebSocket Protocol](docs/reference/WEBSOCKET_PROTOCOL.md) - Exotel WebSocket event reference
- [Exotel API Documentation](https://developer.exotel.com/api)

### AI Providers
- [ElevenLabs Conversational AI](https://elevenlabs.io/docs/conversational-ai/overview)
- [OpenAI API](https://platform.openai.com/docs)
- [Google Gemini](https://ai.google.dev/docs)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Submit a pull request

---

## 📄 License

MIT

---

**Built for Exotel voice automation.** 🚀
