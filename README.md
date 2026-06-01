# 🤖 Voice AI Bot System

A production-ready, conversational AI voice bot that bridges **Exotel's WebSocket streaming** with **OpenAI's Realtime API** for natural, speech-to-speech conversations over phone calls.

## 🎯 What This Bot Does

* **🗣️ Natural Conversations**: Real-time speech-to-speech using OpenAI's latest Realtime API
* **📞 Telephony Integration**: Seamless integration with Exotel's voice streaming services
* **🛑 Smart Interruption**: Handles conversation interruptions naturally
* **🔊 Audio Enhancement**: Built-in noise suppression and audio optimization for telephony
* **⚡ Real-time Processing**: 200ms audio buffering for smooth conversation flow
* **🔒 Security First**: Environment-based configuration, no hardcoded secrets
* **🎵 High-Quality Audio**: 24kHz PCM16 audio format for superior voice quality

## 🇮🇳 Sarvam AI + Agent Stream (Indian languages)

Production integration guide for **Hindi, English, and 10+ Indian languages** on PSTN and browser calls:

**[docs/SARVAM_AGENTSTREAM_INTEGRATION.md](docs/SARVAM_AGENTSTREAM_INTEGRATION.md)**

Includes architecture, Sarvam STT/TTS API patterns, barge-in, rate-limit fallback, deployment checklist, and reference code in [`examples/sarvam_agentstream_pipeline.py`](examples/sarvam_agentstream_pipeline.py).

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key with Realtime API access
- Exotel account with Voicebot Applet access
- *(Optional)* [Sarvam AI](https://www.sarvam.ai) API key for Indian-language STT/TTS — see integration guide above

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Agent-Stream
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

### Configuration

Edit your `.env` file with the following required settings:

```bash
# REQUIRED - Get from OpenAI dashboard
OPENAI_API_KEY=your-openai-api-key-here

# SERVER CONFIG
SERVER_HOST=0.0.0.0
SERVER_PORT=5000

# BOT PERSONALITY
COMPANY_NAME=Your Company Name
SALES_BOT_NAME=Sarah

# AUDIO SETTINGS
SAMPLE_RATE=24000
AUDIO_CHUNK_SIZE=200
```

### Running the Bot

```bash
# Start the bot
python main.py

# Test the configuration
python main.py --config-check

# Run system tests
python main.py --test
```

The bot will start a WebSocket server on `0.0.0.0:5000`.

## 📡 Exotel Integration

### WebSocket URLs

- **Local:** `ws://localhost:5000`
- **Public:** Use ngrok or your server's public IP

### Exotel Voicebot Applet Configuration

1. **URL:** `wss://your-domain.com/?sample-rate=24000`
2. **Sample Rate:** 24kHz (recommended for high quality)
3. **Audio Format:** Raw/slin (16-bit PCM)
4. **Bidirectional Streaming:** Enabled

### Test Message Format

```json
{
  "event": "connected"
}
```

## 🏗️ Project Structure

```
.
├── .env                 # Environment variables (local)
├── .gitignore           # Git ignore file
├── LICENSE              # Project license
├── README.md            # This README file
├── config.py            # Centralized configuration
├── core/                # Core bot logic and framework
│   ├── __init__.py
│   ├── bot_framework.py
│   └── openai_realtime_sales_bot.py
├── engines/             # AI engine components (STT, TTS, NLP, etc.)
│   ├── __init__.py
│   ├── audio_enhancer.py
│   ├── media_resampler.py
│   ├── nlp_engine.py
│   ├── stt_engine.py
│   └── tts_engine.py
├── env.example          # Example environment variables
├── main.py              # Main entry point for the application
├── requirements.txt     # Python dependencies
└── venv/                # Python virtual environment
```

## 🔧 Configuration Options

### Audio Settings

- **SAMPLE_RATE:** Audio sample rate (8000, 16000, 24000)
- **AUDIO_CHUNK_SIZE:** Chunk size in milliseconds (default: 200)
- **BUFFER_SIZE_MS:** Audio buffer size (default: 160)

### Bot Personality

- **COMPANY_NAME:** Your company name
- **SALES_BOT_NAME:** Bot's name
- **OPENAI_VOICE:** Voice selection (coral, nova, shimmer)

### Server Settings

- **SERVER_HOST:** Server host (default: 0.0.0.0)
- **SERVER_PORT:** Server port (default: 5000)

## 🚀 Deployment

### Option 1: Development (ngrok)

```bash
# Install ngrok
./ngrok http 5000
# Use: wss://xxxxx.ngrok-free.app
```

### Option 2: Cloud VPS

```bash
# Setup on DigitalOcean/AWS/GCP
sudo ufw allow 5000
python main.py
# Use: wss://your-server-ip:5000
```

### Option 3: Docker

```bash
# Build and run
docker build -t voice-bot .
docker run --env-file .env -p 5000:5000 voice-bot
```

## 🧪 Testing

### Basic Tests

```bash
# Test configuration
python main.py --config-check

# Test bot connection
python main.py --test
```

### Manual Testing

```bash
# Using wscat
wscat -c ws://localhost:5000

# Send test message
{"event": "connected"}
```

## 🔒 Security

- All sensitive information is stored in environment variables
- No hardcoded API keys or tokens
- `.env` file is gitignored
- Use HTTPS/WSS in production

## 📊 Monitoring

### Key Metrics

- Call Duration
- Bot Response Time
- Audio Quality Score
- Conversation Completion Rate
- Error Rate

### Log Analysis

```bash
# Monitor key events
grep "NEW EXOTEL CONNECTION" logs/bot.log
grep "CONVERSATION COMPLETED" logs/bot.log
grep "ERROR" logs/bot.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Check the troubleshooting section in the README
- Review GitHub Issues for similar problems
- Post detailed issues with logs and configuration

## 🙏 Acknowledgments

- [Exotel](https://www.exotel.com) for voice streaming services
- [OpenAI](https://openai.com) for Realtime API
- [Agent-Stream](https://github.com/exotel/Agent-Stream) for inspiration