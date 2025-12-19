# WebSocket Protocol Documentation

This document describes the WebSocket protocol used for communication between Exotel and the Voice Bot.

## Connection

Connect to the WebSocket endpoint:
```
wss://your-domain.com/media?sample-rate=8000
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample-rate` | integer | 8000 | Audio sample rate (8000, 16000, 24000) |
| Custom params | string | - | Any additional parameters passed to the bot |

### Authentication

If authentication is enabled, provide Basic Auth header:
```
Authorization: Basic base64(api_key:api_token)
```

## Message Format

All messages are JSON objects with an `event` field indicating the message type.

## Incoming Events (Exotel → Bot)

### connected

Sent when WebSocket connection is established.

```json
{
  "event": "connected",
  "protocol": "Exotel Media Stream",
  "version": "1.0.0"
}
```

### start

Sent when a call starts streaming.

```json
{
  "event": "start",
  "sequence_number": "1",
  "start": {
    "call_sid": "abc123",
    "account_sid": "xyz789",
    "from": "+1234567890",
    "to": "+0987654321",
    "media_format": {
      "encoding": "linear16",
      "sample_rate": 8000,
      "bit_rate": 16
    },
    "custom_parameters": {
      "campaign_id": "12345"
    }
  }
}
```

### media

Sent for each audio chunk from the caller.

```json
{
  "event": "media",
  "sequence_number": "2",
  "media": {
    "chunk": "1",
    "timestamp": "1234567890",
    "payload": "base64_encoded_audio_data"
  }
}
```

**Audio Format:**
- Encoding: 16-bit PCM, little-endian
- Channels: Mono
- Sample rate: As specified in `start` event
- Chunk size: 20ms of audio (320 bytes at 8kHz)

### dtmf

Sent when caller presses a key.

```json
{
  "event": "dtmf",
  "sequence_number": "50",
  "dtmf": {
    "digit": "5",
    "duration": "200"
  }
}
```

### stop

Sent when the call ends.

```json
{
  "event": "stop",
  "sequence_number": "100",
  "stop": {
    "call_sid": "abc123",
    "account_sid": "xyz789",
    "reason": "caller_hangup"
  }
}
```

### mark

Sent when a previously sent mark event has been played.

```json
{
  "event": "mark",
  "sequence_number": "75",
  "mark": {
    "name": "greeting-complete"
  }
}
```

## Outgoing Events (Bot → Exotel)

### media

Send audio to the caller.

```json
{
  "event": "media",
  "sequence_number": "1",
  "stream_sid": "stream-uuid",
  "media": {
    "chunk": "1",
    "timestamp": "1234567890",
    "payload": "base64_encoded_audio_data"
  }
}
```

**Requirements:**
- Audio must match the sample rate from `start` event
- Chunk size should be ≥ 3200 bytes (100ms at 8kHz)
- Chunk size must be a multiple of 320 bytes

### mark

Track audio playback position.

```json
{
  "event": "mark",
  "sequence_number": "2",
  "stream_sid": "stream-uuid",
  "mark": {
    "name": "greeting-complete"
  }
}
```

When the audio before this mark is played, Exotel sends back a `mark` event.

### clear

Clear pending audio in the playback queue.

```json
{
  "event": "clear",
  "stream_sid": "stream-uuid"
}
```

Use this when the bot needs to interrupt its own speech (e.g., user started talking).

## Sequence Numbers

- Each message has a `sequence_number` field
- Sequence numbers are strings but contain incrementing integers
- Track sequence numbers for debugging and logging

## Best Practices

### Audio Handling

1. **Buffer audio chunks** before processing (at least 2 seconds)
2. **Send audio in ≥ 100ms chunks** for stable playback
3. **Use early media** (small silence packet) to warm up the audio pipeline
4. **Clear audio queue** before sending new responses to avoid overlap

### Error Handling

1. Handle connection drops gracefully
2. Implement reconnection logic for production
3. Log all events for debugging

### Performance

1. Process audio asynchronously to avoid blocking
2. Use streaming STT for lower latency
3. Consider using streaming TTS for faster response
4. Monitor latency and log performance metrics

## Example Flow

```
Exotel                              Bot
   |                                 |
   |-------- connected ------------->|
   |                                 |
   |-------- start ----------------->|
   |                                 |-- Initialize session
   |                                 |-- Send greeting audio
   |<------- media (greeting) -------|
   |<------- mark (greeting) --------|
   |                                 |
   |-------- media (user audio) ---->|
   |-------- media (user audio) ---->|
   |-------- media (user audio) ---->|
   |                                 |-- Detect silence
   |                                 |-- Transcribe audio
   |                                 |-- Get AI response
   |                                 |-- Generate TTS
   |<------- clear ------------------|
   |<------- media (response) -------|
   |<------- media (response) -------|
   |<------- mark (response) --------|
   |                                 |
   |-------- mark (response) ------->|
   |                                 |-- Response played
   |                                 |
   |-------- stop ------------------>|
   |                                 |-- Cleanup session
```

## Error Codes

| Code | Description |
|------|-------------|
| 1000 | Normal closure |
| 1001 | Server shutting down |
| 1008 | Unauthorized (auth failed) |
| 1011 | Internal server error |

