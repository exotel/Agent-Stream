# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added

#### Bots
- **OpenAI Realtime Bot** - True speech-to-speech with GPT-4o Realtime API (~500ms latency)
- **ElevenLabs Bridge** - All-in-one conversational AI (~750ms latency)
- **Gemini Speech-to-Speech** - Gemini 2.5 Flash + OpenAI TTS
- **OpenAI Pipeline Bot** - Whisper STT + GPT-4 + OpenAI TTS
- **Simple Conversation Bot** - Basic GPT-4 conversation

#### Core Features
- WebSocket server for Exotel bidirectional streaming
- Audio resampling (8kHz ↔ 16kHz ↔ 24kHz)
- Noise cancellation (RNNoise, Spectral)
- Barge-in support (user interruption handling)
- Pre-cached greetings for instant playback

#### Utilities
- `SessionState` - Turn-taking state machine
- `AudioUtils` - Audio chunking, level detection
- `BargeInHandler` - Interruption handling
- `ExotelApi` - REST API client for making calls

#### Infrastructure
- Docker and Docker Compose support
- Health check endpoints
- Structured logging with correlation IDs
- Jest testing framework
- ESLint configuration
- TypeScript support

#### Documentation
- Comprehensive README
- Developer Quickstart guide
- Best Practices guide
- WebSocket Protocol reference
- Exotel Integration Issues guide
- AI Bot Issues & Mitigations guide

### Fixed
- Audio chunk size validation (3200 bytes minimum)
- Race conditions in audio processing
- Turn-taking with proper state management
- Greeting latency (reduced from ~2s to ~1ms)

## [0.1.0] - 2024-12-01

### Added
- Initial project setup
- Basic WebSocket server
- Simple echo bot example

