# Source Code Structure

```
src/
├── index.js              # Main entry point & exports
│
├── core/                 # Framework (don't modify unless extending)
│   ├── server.js         # WebSocket server
│   ├── config.js         # Configuration
│   ├── handlers/         # Message handling
│   ├── utils/            # Utilities (logger, resampler, botUtils)
│   └── audio/            # Audio processing
│
├── bots/                 # Bot implementations (copy & customize)
│   ├── realtime/         # True S2S - lowest latency
│   │   └── openai-realtime-bot.js
│   │
│   ├── conversational/   # All-in-one AI agents
│   │   └── elevenlabs-bridge.js
│   │
│   ├── pipeline/         # STT → LLM → TTS (most flexible)
│   │   ├── openai-bot.js
│   │   ├── gemini-bot.js
│   │   └── simple-bot.js
│   │
│   └── experimental/     # Beta features
│       ├── gemini-live-bridge.js
│       └── gemini-elevenlabs-bot.js
│
├── middleware/           # Express middleware
├── services/             # Business logic services
└── types/                # TypeScript type definitions
```

## Quick Start

### Using the Framework

```javascript
const { createServer, MessageHandler, BotUtils } = require('./src');

// Create your custom bot using the framework
```

### Running a Bot

```bash
# Production bots
npm run openai-realtime   # Fastest
npm run elevenlabs-bot    # Best quality

# Development
npm start                 # Simple chat bot
```

## Bot Categories

| Category | Latency | Best For |
|----------|---------|----------|
| `realtime/` | ~500ms | Production, low latency |
| `conversational/` | ~750ms | Best voice quality |
| `pipeline/` | ~4s | Custom logic, flexibility |
| `experimental/` | varies | Testing new APIs |

