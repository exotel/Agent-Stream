# Voice Bot Best Practices

Comprehensive guide for building low-latency, production-ready voice bots with Exotel.

## Table of Contents
1. [Latency Optimization](#latency-optimization)
2. [Audio Handling](#audio-handling)
3. [Turn-Taking](#turn-taking)
4. [Barge-In Handling](#barge-in-handling)
5. [Error Handling](#error-handling)
6. [Session Management](#session-management)

---

## Latency Optimization

### 1. Pre-Cache Greeting Audio

**Problem**: Generating greeting on each call adds 2-3s latency.

**Solution**: Generate and cache greeting audio at bot startup.

```javascript
class MyBot extends ExotelWSSServer {
  constructor() {
    super();
    this.cachedGreeting = null;
    this.cacheGreeting(); // Cache on startup
  }

  async cacheGreeting() {
    const response = await openai.audio.speech.create({
      model: 'tts-1',
      voice: 'alloy',
      input: "Hi! How can I help you today?",
      response_format: 'pcm'
    });
    
    const audioData = Buffer.from(await response.arrayBuffer());
    // Resample from 24kHz to 8kHz for Exotel
    this.cachedGreeting = AudioResampler.resample(audioData, 24000, 8000);
  }
}
```

**Result**: Greeting sent in ~1ms instead of ~2000ms.

### 2. Parallel AI Connection

**Problem**: Waiting for AI connection blocks greeting.

**Solution**: Send cached greeting while connecting to AI in background.

```javascript
onStart: async (streamInfo) => {
  // Send greeting IMMEDIATELY
  if (this.cachedGreeting) {
    AudioUtils.sendAudioChunked(sender, this.cachedGreeting);
  }
  
  // Connect to AI in background (non-blocking)
  this.connectToAI(session, sender).catch(err => {
    logger.error('AI connection failed:', err.message);
  });
}
```

### 3. Faster Silence Detection

**Problem**: Long silence threshold delays processing.

**Solution**: Reduce silence threshold (but not too much).

```javascript
// Optimized values
silenceThreshold: 8,     // ~160ms (was 15 = 300ms)
minAudioChunks: 25,      // ~500ms (was 80 = 2s)
processingCooldown: 800  // 800ms (was 1500ms)
```

---

## Audio Handling

### 1. Proper Chunk Size

**Problem**: Exotel requires minimum 3200-byte chunks.

**Solution**: Always send 3200-byte chunks, pad final chunk.

```javascript
const { AudioUtils, EXOTEL_CONSTANTS } = require('../src/utils/botUtils');

// Send audio in proper chunks
AudioUtils.sendAudioChunked(sender, audioBuffer);

// Or manually:
const CHUNK_SIZE = 3200; // 200ms at 8kHz
for (let i = 0; i < audio.length; i += CHUNK_SIZE) {
  const chunk = audio.slice(i, Math.min(i + CHUNK_SIZE, audio.length));
  if (chunk.length < CHUNK_SIZE) {
    const padded = Buffer.alloc(CHUNK_SIZE, 0);
    chunk.copy(padded);
    sender.sendMedia(padded);
  } else {
    sender.sendMedia(chunk);
  }
}
```

### 2. Audio Resampling

**Problem**: Different services use different sample rates.

**Solution**: Use AudioResampler for conversions.

```javascript
const AudioResampler = require('../src/utils/audioResampler');

// Exotel (8kHz) ↔ OpenAI/ElevenLabs (16kHz/24kHz)
const audio16k = AudioResampler.resample(audio8k, 8000, 16000);
const audio8k = AudioResampler.resample(audio24k, 24000, 8000);
```

### 3. Audio Level Detection

**Problem**: Need to detect silence vs speech.

**Solution**: Calculate audio level from PCM samples.

```javascript
const { AudioUtils } = require('../src/utils/botUtils');

const level = AudioUtils.calculateAudioLevel(audioBuffer);
const isSilent = level < 300; // Threshold

// Or check directly
if (AudioUtils.isSilent(audioBuffer)) {
  silenceCounter++;
}
```

---

## Turn-Taking

### 1. Use SessionState

**Problem**: Race conditions with concurrent processing.

**Solution**: Use SessionState class for proper state management.

```javascript
const { SessionState } = require('../src/utils/botUtils');

const state = new SessionState(streamId);

// Check if can process
if (state.canProcess()) {
  const audio = state.startProcessing(); // Locks immediately
  // ... process audio ...
  state.finishProcessing();
}

// Track speaking state
state.startSpeaking();
// ... send audio ...
state.stopSpeaking();
```

### 2. Synchronous Flag Setting

**Problem**: Async processing causes multiple concurrent AI calls.

**Solution**: Set flags synchronously BEFORE async operations.

```javascript
// ❌ WRONG: Race condition
if (!session.isProcessing) {
  processAudio().then(() => {
    session.isProcessing = false;
  });
}

// ✅ CORRECT: Synchronous lock
if (!session.isProcessing) {
  session.isProcessing = true;  // Lock immediately!
  const audioToProcess = [...session.audioBuffer];
  session.audioBuffer = [];     // Clear immediately!
  
  processAudio(audioToProcess).finally(() => {
    session.isProcessing = false;
  });
}
```

### 3. Skip During Playback

**Problem**: Processing input while bot is speaking causes echo.

**Solution**: Skip audio forwarding when bot is speaking.

```javascript
onMedia: (mediaData) => {
  // Skip if bot is speaking
  if (session.state.isBotSpeaking) {
    return;
  }
  
  // Process incoming audio
  this.forwardAudioToAI(session, mediaData.audioBuffer);
}
```

---

## Barge-In Handling

### 1. Detect User Interruption

**Problem**: User can't interrupt bot mid-sentence.

**Solution**: Detect speech during bot audio and stop playback.

```javascript
const { BargeInHandler, AudioUtils } = require('../src/utils/botUtils');

onMedia: (mediaData) => {
  const isSilent = AudioUtils.isSilent(mediaData.audioBuffer);
  
  // Barge-in: user speaks while bot is talking
  if (!isSilent && session.state.isBotSpeaking) {
    BargeInHandler.handle(session.state, sender, aiConnection);
    return;
  }
}
```

### 2. Clear Event

**Problem**: Need to stop Exotel's audio buffer.

**Solution**: Send `clear` event to stop playback.

```javascript
// In BargeInHandler or manually:
sender.sendClear();
session.state.isBotSpeaking = false;

// Also cancel AI response if possible
if (aiConnection) {
  aiConnection.send(JSON.stringify({ type: 'response.cancel' }));
}
```

---

## Error Handling

### 1. Connection Failures

```javascript
try {
  await this.connectToAI(session, sender);
} catch (error) {
  logger.error('AI connection failed:', error.message);
  
  // Send error message to user
  const errorAudio = await this.generateTTS("Sorry, I'm having trouble. Please try again.");
  AudioUtils.sendAudioChunked(sender, errorAudio);
}
```

### 2. Processing Errors

```javascript
try {
  await this.processAudio(audioBuffer);
} catch (error) {
  logger.error('Processing error:', error.message);
  session.isProcessing = false;  // Reset state
  session.isBotSpeaking = false;
}
```

---

## Session Management

### 1. Proper Cleanup

```javascript
onStop: (stopData) => {
  // Clear intervals
  if (session.processingInterval) {
    clearInterval(session.processingInterval);
  }
  
  // Close AI connection
  if (session.aiConnection) {
    session.aiConnection.close();
  }
  
  // Clear buffers
  session.audioBuffer = [];
  
  // Remove session
  this.sessions.delete(streamId);
}
```

### 2. Early Media

Send silence at call start to establish audio path.

```javascript
onStart: (streamInfo) => {
  AudioUtils.sendEarlyMedia(sender);
  // Continue with greeting...
}
```

---

## Quick Reference

### Shared Utilities

```javascript
const { 
  SessionState,      // Turn-taking state machine
  AudioUtils,        // Audio chunking, level detection
  BargeInHandler,    // Interruption handling
  EXOTEL_CONSTANTS   // Audio format specs
} = require('../src/utils/botUtils');
```

### Exotel Constants

| Constant | Value | Description |
|----------|-------|-------------|
| SAMPLE_RATE | 8000 | Hz |
| BITS_PER_SAMPLE | 16 | bit |
| MIN_CHUNK_SIZE | 3200 | bytes (200ms) |
| BYTES_PER_CHUNK | 320 | bytes (20ms) |
| SILENCE_THRESHOLD | 300 | Audio level |

### Latency Targets

| Metric | Target | Acceptable |
|--------|--------|------------|
| Greeting | <10ms | <100ms |
| AI Response | <500ms | <2s |
| Total Round-Trip | <1s | <3s |

---

## Checklist for New Bots

- [ ] Pre-cache greeting audio
- [ ] Use SessionState for turn-taking
- [ ] Send 3200-byte chunks
- [ ] Handle barge-in
- [ ] Skip processing during playback
- [ ] Send early media
- [ ] Clean up on session end
- [ ] Handle errors gracefully

