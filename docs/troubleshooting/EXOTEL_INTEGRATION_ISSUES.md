# Exotel Voice Bot Integration Issues and Best Practices

A practical guide to common issues when integrating AI voice bots with Exotel's voice/telephony platform (AgentStream/Voicebot applets), along with fixes and best practices.

---

## 📌 1. WebSocket Connection Failures

### Issue
The bot server never connects or drops immediately after connection when Exotel initiates the voice stream.

### Common Causes
* WebSocket URL is not publicly reachable or has invalid TLS (self-signed certs often rejected)
* Endpoint times out because the bot didn't respond in time. Exotel expects responses within ~10s
* Network firewall/NAT blocks WSS traffic
* Using plain HTTP/S instead of WSS in Voicebot applet config

### Fixes / Best Practices

✅ Set up a **public wss:// endpoint** with a valid domain + valid TLS certificate

✅ Ensure your bot server **responds immediately** (even a simple handshake) before processing audio

✅ Use **connection retries and monitoring** on your server to reconnect if dropped

✅ Whitelist Exotel IPs or ensure traffic isn't blocked by firewalls

### Implementation in This Project

```javascript
// src/server.js - Immediate response on connection
this.wss.on('connection', (ws, req) => {
  // Log connection immediately
  logger.info(`🔌 New WebSocket Connection`);
  
  // Authenticate quickly
  const authenticated = this.authenticate(req);
  if (!authenticated) {
    ws.close(1008, 'Unauthorized');
    return;
  }
  
  // Set up handlers immediately - don't block
  // ...
});
```

---

## 🔊 2. Audio Format / Chunking Problems

### Issue
Audio appears distorted, has gaps, or streams incorrectly to/from the bot.

### Common Causes
* Exotel sends **Base64-encoded 16-bit, 8 kHz PCM** audio. If your bot expects a different format, decoding mismatches happen
* Streaming chunk sizes outside the recommended range (3.2 kB to 100 kB, multiples of 320 bytes)
* Incomplete frame handling leads to audio artifacts

### Fixes

✅ Convert/normalize audio to **match Exotel's format** exactly before feeding into ASR/AI pipeline

✅ Respect the **chunk size rules** (minimum 3200 bytes = 200ms at 8kHz); implement buffering

✅ Implement audio resampling if your AI engine runs at different rates

### Implementation in This Project

```javascript
// examples/gemini-speech-to-speech-bot.js - Proper chunk sizing
const CHUNK_SIZE = 3200; // 200ms at 8kHz, 16-bit - Exotel minimum

for (let i = 0; i < resampledAudio.length; i += CHUNK_SIZE) {
  const chunk = resampledAudio.slice(i, Math.min(i + CHUNK_SIZE, resampledAudio.length));
  
  // Pad final chunk if needed to meet minimum size
  if (chunk.length < CHUNK_SIZE && chunk.length > 0) {
    const paddedChunk = Buffer.alloc(CHUNK_SIZE, 0);
    chunk.copy(paddedChunk);
    sender.sendMedia(paddedChunk);
  } else {
    sender.sendMedia(chunk);
  }
}
```

```javascript
// src/utils/audioResampler.js - Format conversion
const AudioResampler = require('./utils/audioResampler');

// Convert from OpenAI TTS (24kHz) to Exotel (8kHz)
const exotelAudio = AudioResampler.resample(ttsAudio, 24000, 8000);

// Convert from Exotel (8kHz) to Gemini (16kHz)  
const geminiAudio = AudioResampler.resample(exotelAudio, 8000, 16000);
```

---

## 🕐 3. Timeouts and Session Limits

### Issue
Calls drop unexpectedly or streaming shuts before expected.

### Causes
* Sessions have a **maximum time** enforced (often around 60 min)
* No heartbeat or keepalive on long sessions

### Fixes

✅ Implement periodic **keepalive / ping messages** in WebSocket to keep sessions alive

✅ Monitor audio events for "stop" / termination events and handle cleanup gracefully

### Implementation in This Project

```javascript
// src/server.js - WebSocket keepalive
this.keepaliveInterval = setInterval(() => {
  this.wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      return ws.terminate();
    }
    ws.isAlive = false;
    ws.ping(); // Send ping every 30 seconds
  });
}, 30000);

// Handle pong responses
ws.on('pong', () => {
  ws.isAlive = true;
});
```

---

## 🪪 4. Incorrect Call Flow or Applet Setup

### Issue
Bot never receives audio or calls don't route into your AI pipeline.

### Causes
* Voicebot or Stream Applet not added in the **call flow** in Exotel App Bazaar
* Missing **Passthru** applet when expected metadata or control flow is needed
* Applet not enabled (requires Exotel support / KYC before activation)

### Fixes

✅ In App Bazaar, include the **Voicebot Applet** at the right stage

✅ If you just need audio for STT/analytics, use the **Stream Applet**

✅ Request Exotel support to **enable streaming capabilities** on your account if applets aren't visible

### Exotel Call Flow Example

```
Incoming Call → Greeting Applet → Voicebot Applet (WSS URL) → End Call
                                        ↓
                              wss://your-server.com/media
```

---

## 📊 5. DTMF (Keypad) and Control Events Not Handled

### Issue
User pressing keypad digits is not triggering expected logic in bot flows.

### Cause
Bot logic isn't decoding or routing DTMF events from Exotel's WebSocket payload.

### Fixes

✅ Deserialize **DTMF events** correctly from the stream

✅ Map DTMF to intents or control paths in your bot logic

### Implementation in This Project

```javascript
// src/handlers/messageHandler.js - DTMF handling
case 'dtmf':
  this.eventLogger.logDTMF(data);
  if (callbacks.onDTMF) {
    callbacks.onDTMF({
      digit: data.digit,
      timestamp: data.timestamp
    });
  }
  break;

// In your bot:
onDTMF: (dtmfData) => {
  logger.info(`🔢 DTMF: ${dtmfData.digit}`);
  
  switch (dtmfData.digit) {
    case '1':
      // Sales intent
      break;
    case '2':
      // Support intent
      break;
    case '#':
      // End call
      ws.close(1000, 'User ended call');
      break;
  }
}
```

---

## ⚙️ 6. Latency & Real-Time Constraints

### Issue
Bot responses feel "laggy" or delayed, harming UX.

### Causes
* Round-trip latency between Exotel streaming and your AI model back to caller
* No audio buffering strategy
* Greeting generated on-demand instead of pre-cached

### Fixes

✅ **Pre-cache greeting audio** on bot startup for instant playback

✅ Pre-buffer audio frames (e.g., 200–300 ms) before sending to ASR/AI for better throughput

✅ Deploy bot logic close to your Exotel instance region to reduce network latency

✅ Use faster real-time models where possible

### Implementation in This Project

```javascript
// examples/gemini-speech-to-speech-bot.js - Pre-cached greeting
class GeminiSpeechBot extends ExotelWSSServer {
  constructor() {
    super();
    this.cachedGreeting = null;
    
    // Pre-cache greeting on startup
    this.preCacheGreeting();
  }

  async preCacheGreeting() {
    logger.info('⏳ Pre-caching greeting audio...');
    
    const response = await this.openai.audio.speech.create({
      model: 'tts-1',
      voice: 'alloy',
      input: "Hi! I'm powered by Gemini. How can I help you today?",
      response_format: 'pcm',
      speed: 1.1
    });

    const audioData = Buffer.from(await response.arrayBuffer());
    this.cachedGreeting = AudioResampler.resample(audioData, 24000, 8000);
    
    logger.info(`✅ Greeting cached (${this.cachedGreeting.length} bytes)`);
  }

  async sendGreeting(streamId, sender) {
    // Use cached greeting for instant playback (< 50ms vs 2-3s)
    if (this.cachedGreeting) {
      // Send immediately - no API call needed!
      this.sendAudioChunks(sender, this.cachedGreeting);
    }
  }
}
```

---

## 🔒 7. Security / Token Handling Problems

### Issue
Authentication with Exotel APIs or WebSocket fails.

### Causes
* Expired API keys or missing proper headers
* Using insecure or improper token formats

### Fixes

✅ Rotate API keys securely and store in environment variables

✅ Ensure WebSocket handshake includes any required auth headers or tokens

### Implementation in This Project

```javascript
// src/config.js - Secure configuration
module.exports = {
  authentication: {
    enabled: process.env.AUTH_ENABLED !== 'false',
    token: process.env.AUTH_TOKEN
  }
};

// src/server.js - Authentication
authenticate(req) {
  if (!config.authentication.enabled) return true;
  
  const url = new URL(req.url, `http://${req.headers.host}`);
  const token = url.searchParams.get('token') || 
                req.headers['authorization']?.replace('Bearer ', '');
  
  return token === config.authentication.token;
}
```

---

## 🧪 8. Integration with OpenAI / STT / TTS Backend

### Issue
Your OpenAI model responses aren't transmitted correctly over voice streams.

### Causes
* Codec mismatch between TTS output and PCM audio for Exotel
* Lack of intermediate conversion logic

### Fixes

✅ Convert OpenAI TTS output to **8 kHz PCM** for Exotel playback

✅ Use an audio pipeline that standardizes all audio paths (input/output) at the expected sampling rate/encoding

### Audio Format Reference

| Service | Input Format | Output Format |
|---------|--------------|---------------|
| **Exotel** | 8kHz 16-bit PCM | 8kHz 16-bit PCM |
| **OpenAI TTS** | - | 24kHz 16-bit PCM |
| **OpenAI Whisper** | 16kHz 16-bit PCM | - |
| **Gemini** | 16kHz 16-bit PCM | - |
| **ElevenLabs** | 16kHz 16-bit PCM | 16kHz 16-bit PCM |

### Implementation in This Project

```javascript
// Audio conversion pipeline
// 1. Exotel (8kHz) → Gemini (16kHz)
const geminiInput = AudioResampler.resample(exotelAudio, 8000, 16000);

// 2. Gemini processes and returns text
const aiResponse = await gemini.generateContent(geminiInput);

// 3. OpenAI TTS (24kHz) → Exotel (8kHz)
const ttsAudio = await openai.audio.speech.create({ ... });
const exotelOutput = AudioResampler.resample(ttsAudio, 24000, 8000);

// 4. Send to Exotel in proper chunks
sender.sendMedia(exotelOutput);
```

---

## 🛠 9. Observability & Debugging Gaps

### Issue
Troubleshooting complex integrations is hard without visibility.

### Fixes

✅ Log WebSocket events (connected, start, media, dtmf, stop, clear)

✅ Capture latency, packet sizes, errors, and call IDs for diagnostics

✅ Use structured logs and dashboards for production metrics

### Implementation in This Project

```javascript
// src/utils/eventLogger.js - Comprehensive logging
class EventLogger {
  logConnection(data) {
    this.log('CONNECTION', 'CONNECTION ESTABLISHED', data);
  }

  logStreamStart(data) {
    this.log('STREAM_START', 'STREAM STARTED', {
      callSid: data.call_sid,
      from: data.from,
      to: data.to,
      sampleRate: data.sampleRate
    });
  }

  logMedia(data) {
    this.stats.mediaChunks++;
    // Log every 50th chunk to avoid spam
    if (this.stats.mediaChunks % 50 === 0) {
      this.logger.debug(`📦 Media: ${this.stats.mediaChunks} chunks received`);
    }
  }

  // Session summary on disconnect
  logSessionSummary() {
    this.log('SUMMARY', 'SESSION SUMMARY', {
      totalDuration: this.getSessionDuration(),
      totalEvents: this.stats.totalEvents,
      eventBreakdown: this.stats.eventCounts
    });
  }
}
```

---

## 📌 Quick Troubleshooting Checklist

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Bot never connects | Wrong WebSocket setup | Ensure WSS, valid TLS, reachable endpoint |
| Audio stutters or gaps | Bad chunk handling | Buffer + respect packet size (≥3200 bytes) |
| Calls drop mid-session | Timeout | Heartbeat + monitor keepalive |
| DTMF ignored | Missing decoding | Map DTMF events in bot |
| Model replies not heard | Format mismatch | Convert TTS to PCM 8 kHz |
| Events not firing | Applet misconfig | Confirm call flow applet order |
| High latency greeting | TTS on-demand | Pre-cache greeting audio on startup |
| Connection rejected | Auth failure | Check token/API key configuration |

---

## 🔗 References

1. [Working with the Stream and Voicebot Applet](https://support.exotel.com/support/solutions/articles/3000108630)
2. [Working with the Stream and Voicebot Applet (Beta)](https://support.exotel.com/support/solutions/articles/3000132302)
3. [Quick Guide to Get Started with Exotel Streaming Services](https://support.exotel.com/support/solutions/articles/3000132268)
4. [Exotel AgentStream Integration with Pipecat](https://exotel.com/blog/exotel-pipecat-agentstream-guide/)

---

## 📋 Production Checklist

Before deploying your Exotel voice bot to production:

- [ ] **WSS endpoint** is publicly accessible with valid TLS
- [ ] **Audio chunks** are ≥3200 bytes (200ms at 8kHz)
- [ ] **Keepalive/ping** is implemented for long sessions
- [ ] **Greeting is pre-cached** for instant playback
- [ ] **Audio resampling** handles format conversion correctly
- [ ] **DTMF handling** is implemented
- [ ] **Error handling** provides graceful degradation
- [ ] **Logging** captures all events for debugging
- [ ] **Health check** endpoint is available
- [ ] **Exotel flow** is configured correctly in App Bazaar

