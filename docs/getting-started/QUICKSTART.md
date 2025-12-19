# Developer Quickstart Guide

Get a voice bot running in under 5 minutes.

## Prerequisites

- Node.js 18+
- ngrok (for exposing local server)
- Exotel account with WebSocket streaming enabled
- API key from at least one AI provider

## Step 1: Install

```bash
git clone <repository>
cd exotel-voice-bot
npm install
```

## Step 2: Configure

```bash
cp .env.example .env
```

Add your API keys:

```bash
# Choose ONE of these options:

# Option A: ElevenLabs (Recommended - lowest latency)
ELEVENLABS_API_KEY=your-key
ELEVENLABS_AGENT_ID=your-agent-id

# Option B: Gemini + OpenAI TTS
GEMINI_API_KEY=AIza-your-key
OPENAI_API_KEY=sk-your-key

# Exotel API (for making calls)
EXOTEL_API_KEY=your-key
EXOTEL_API_TOKEN=your-token
EXOTEL_ACCOUNT_SID=Exotel
EXOTEL_VIRTUAL_NUMBER=+91YYYYYYYYYY
EXOTEL_FLOW_ID=YOUR_FLOW_ID
```

## Step 3: Start Bot

```bash
# ElevenLabs (recommended)
npm run elevenlabs-bot

# Or Gemini
npm run gemini-bot
```

## Step 4: Expose with ngrok

In a new terminal:

```bash
ngrok http 5001
```

Copy the `https://xxx.ngrok.io` URL.

## Step 5: Configure Exotel Flow

1. Go to Exotel Dashboard → Flows
2. Edit your flow (ID: YOUR_FLOW_ID)
3. In the WebSocket applet, set URL: `wss://xxx.ngrok.io/media`
4. Save the flow

## Step 6: Make a Test Call

```bash
npm run call 9876543210
```

---

## Architecture Options

### Option 1: ElevenLabs Conversational AI (Recommended)

**Best for:** Production deployments, natural conversation

```
Exotel ←→ Your Bot ←→ ElevenLabs (STT + LLM + TTS in one)
```

- ✅ Sub-second latency (~750ms)
- ✅ Natural turn-taking
- ✅ Built-in conversation logic
- ✅ No separate AI services needed

```bash
npm run elevenlabs-bot
```

### Option 2: Gemini + OpenAI TTS

**Best for:** Custom AI logic, Google ecosystem

```
Exotel ←→ Your Bot ←→ Gemini (audio understanding) + OpenAI (TTS)
```

- ⚡ 5-6 second latency (API limitations)
- ✅ Multimodal capabilities
- ✅ Custom conversation logic

```bash
npm run gemini-bot
```

### Option 3: Custom STT → LLM → TTS

**Best for:** Full control, custom AI

```
Exotel ←→ Your Bot ←→ Whisper/Deepgram (STT) → GPT-4 (LLM) → OpenAI TTS
```

- ⚡ 2-4 second latency
- ✅ Full customization
- ✅ Any AI provider

```bash
npm run s2s-bot
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/server.js` | Core WebSocket server |
| `src/handlers/messageSender.js` | Send media/clear/mark to Exotel |
| `src/handlers/messageHandler.js` | Parse incoming Exotel messages |
| `src/utils/audioResampler.js` | 8kHz ↔ 16kHz conversion |
| `src/utils/exotelApi.js` | Exotel REST API client |
| `examples/*.js` | Bot implementations |

---

## Common Operations

### Send Audio to Caller

```javascript
// In your bot's callback
sender.sendMedia(audioBuffer);  // Buffer of PCM audio
```

### Clear Audio (Barge-in)

```javascript
// Stop current playback so user can speak
sender.sendClear();
```

### Track Playback

```javascript
// Send mark after audio
sender.sendMark('response-1');

// Listen for mark event
onMark: (data) => {
  console.log('Audio played:', data.name);
}
```

### Make API Call

```javascript
const ExotelApi = require('./src/utils/exotelApi');
const exotel = new ExotelApi();

await exotel.makeCall({
  from: '9876543210',
  to: '+91YYYYYYYYYY',
  callerId: '+91YYYYYYYYYY',
  flowUrl: 'http://my.exotel.com/Exotel/exoml/start_voice/YOUR_FLOW_ID'
});
```

---

## Debugging

### Check Bot Health

```bash
curl http://localhost:5001/health
```

### View Logs

```bash
# Structured JSON logs
tail -f /tmp/bot.log | jq .

# Or run in foreground
npm run elevenlabs-bot 2>&1 | tee /tmp/bot.log
```

### Test WebSocket

```bash
wscat -c ws://localhost:5001/media
# Send: {"event":"connected"}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No audio | Check audio format (16-bit PCM 8kHz) |
| High latency | Use ElevenLabs bot instead |
| Connection drops | Check ngrok is running |
| 403 from Exotel | Verify API credentials |
| Bot doesn't respond | Check AI provider API key |

---

## Next Steps

1. Read [Event Flow & Latency](EVENT_FLOW_AND_LATENCY.md) for optimization
2. Read [Exotel Integration Issues](EXOTEL_INTEGRATION_ISSUES.md) for common problems
3. Customize bot prompts in ElevenLabs dashboard or code
4. Deploy with Docker: `npm run docker:build && npm run docker:run`

