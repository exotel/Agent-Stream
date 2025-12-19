# Exotel ↔ Bot Event Flow & Latency Analysis

## 📊 Complete Event Mapping

### Exotel → Bot Events

| Exotel Event | Bot Handler | When Triggered | Bot Action |
|--------------|-------------|----------------|------------|
| `connected` | `handleConnected()` | WebSocket established | Log connection |
| `start` | `handleStart()` → `onStart()` | Call begins streaming | Send greeting |
| `media` | `handleMedia()` → `onMedia()` | Every 40ms (320 bytes) | Buffer audio, detect silence |
| `dtmf` | `handleDTMF()` → `onDTMF()` | User presses keypad | Handle digit |
| `mark` | `handleMark()` → `onMark()` | Audio playback milestone | Track playback |
| `stop` | `handleStop()` → `onStop()` | Call ends | Cleanup |

### Bot → Exotel Events

| Bot Action | Exotel Event | Purpose |
|------------|--------------|---------|
| `sender.sendMedia(buffer)` | `media` | Send audio to caller |
| `sender.sendClear()` | `clear` | Stop current audio (barge-in) |
| `sender.sendMark(name)` | `mark` | Track audio playback |

---

## ⏱️ Latency Breakdown (Before Optimization)

```
User Speaks (2s min) → Silence (300ms) → Gemini (3.5s) → TTS (1.7s) → Audio Send
         ↑                    ↑                ↑              ↑           ↑
     2000ms             300ms            3500ms         1700ms        50ms
     
TOTAL: ~7.5 seconds from end of speech to hearing response!
```

### Latency Sources

| Source | Current | Issue |
|--------|---------|-------|
| **Min audio buffer** | 80 chunks (2s) | Waiting too long for user to speak |
| **Silence threshold** | 15 chunks (300ms) | OK, but could be faster |
| **Processing cooldown** | 1500ms | Prevents rapid responses |
| **Interval check** | 2000ms | Backup trigger too slow |
| **Gemini API** | ~3500ms | Slow LLM processing |
| **OpenAI TTS** | ~1700ms | TTS generation |
| **Audio chunking** | ~50ms | Minimal |

---

## 🚀 Optimizations Applied

### 1. Reduced Audio Buffer Minimum
- **Before:** 80 chunks (2 seconds minimum speech)
- **After:** 25 chunks (0.5 seconds minimum speech)

### 2. Faster Silence Detection
- **Before:** 15 chunks (300ms silence)
- **After:** 8 chunks (160ms silence)

### 3. Shorter Processing Cooldown
- **Before:** 1500ms between responses
- **After:** 800ms between responses

### 4. Faster Backup Interval
- **Before:** 2000ms interval check
- **After:** 1000ms interval check

---

## ⏱️ Latency Breakdown (After Optimization)

```
User Speaks (0.5s min) → Silence (160ms) → Gemini (3.5s) → TTS (1.7s) → Audio Send
         ↑                     ↑                ↑              ↑           ↑
       500ms              160ms            3500ms         1700ms        50ms
     
TOTAL: ~5.9 seconds from end of speech to hearing response
IMPROVEMENT: ~1.6 seconds faster!
```

---

## 📈 Further Optimization Opportunities

### Model-Level Optimizations

| Optimization | Current | Potential | Savings |
|--------------|---------|-----------|---------|
| **Use GPT-4o-mini instead of Gemini** | 3500ms | ~1500ms | 2000ms |
| **Use tts-1 with speed 1.2** | 1700ms | ~1400ms | 300ms |
| **Parallel processing** | Sequential | Parallel | Variable |
| **Streaming TTS** | Full buffer | Chunked | ~500ms |

### Architecture-Level Optimizations

1. **Use ElevenLabs Conversational AI** - All-in-one, ~750ms latency
2. **Use OpenAI Realtime API** - Native audio, ~500ms latency
3. **Use Gemini Live API** - Native audio (requires paid plan)

---

## 🔧 Configuration Tuning

```javascript
// Optimized session parameters
initializeSession(streamId) {
  return {
    silenceThreshold: 8,      // 160ms silence (was 15 = 300ms)
    minAudioChunks: 25,       // 0.5s minimum (was 80 = 2s)
    processingCooldown: 800,  // 800ms cooldown (was 1500ms)
    intervalCheck: 1000       // 1s interval (was 2000ms)
  };
}
```

---

## 📋 Event Timeline Example

### Optimized Call Flow

```
T+0.000s  [EXOTEL→BOT]  connected
T+0.001s  [EXOTEL→BOT]  start {call_sid, from, to}
T+0.002s  [BOT→EXOTEL]  media (early silence - 200ms)
T+0.003s  [BOT→EXOTEL]  clear
T+0.005s  [BOT→EXOTEL]  media (cached greeting - 14 chunks)
T+0.050s  [BOT→EXOTEL]  mark (greeting-complete)
T+0.100s  [EXOTEL→BOT]  media (user audio chunk 1)
T+0.140s  [EXOTEL→BOT]  media (user audio chunk 2)
...
T+0.600s  [EXOTEL→BOT]  media (user audio chunk 25) ← Min buffer reached
T+0.640s  [EXOTEL→BOT]  media (silence detected)
T+0.800s  [BOT]         Processing triggered (8 silence chunks)
T+0.810s  [BOT]         → Sending to Gemini API
T+4.310s  [BOT]         ← Gemini response received (3500ms)
T+4.320s  [BOT]         → Sending to OpenAI TTS
T+6.020s  [BOT]         ← TTS audio received (1700ms)
T+6.025s  [BOT→EXOTEL]  clear
T+6.030s  [BOT→EXOTEL]  media (response chunk 1)
...
T+8.030s  [BOT→EXOTEL]  mark (response-complete)
```

---

## 🎯 Target Latencies by Architecture

| Architecture | End-to-End Latency | Notes |
|--------------|-------------------|-------|
| **ElevenLabs Conversational AI** | 750ms - 1.5s | Best for production |
| **OpenAI Realtime API** | 500ms - 1s | Requires special access |
| **Gemini + OpenAI TTS (optimized)** | 5-6s | Current implementation |
| **Gemini + OpenAI TTS (original)** | 7-8s | Before optimization |

