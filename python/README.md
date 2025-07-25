# NLP Sales Bot - Voice Streaming AI Assistant

An intelligent sales bot powered by OpenAI GPT, speech recognition, and natural language processing. This bot handles voice calls through Exotel, automatically qualifies leads, and provides personalized product recommendations.

## 🚀 Features

- **🗣️ Voice Conversation**: Real-time speech-to-text and text-to-speech processing
- **🧠 Advanced NLP**: Intent recognition, sentiment analysis, and entity extraction
- **🎯 Lead Qualification**: Automatic lead scoring and qualification
- **💬 Intelligent Responses**: Context-aware responses powered by OpenAI GPT
- **📊 Analytics**: Conversation tracking and performance metrics
- **🔗 CRM Integration**: Webhook support for qualified leads
- **🎛️ Configurable**: Easy customization of products, responses, and behavior

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Exotel Call   │───▶│  WebSocket Server │───▶│   Sales Bot     │
│   (Voice)       │    │  (app.py)        │    │  (NLP Engine)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Speech Handler  │    │  Lead Scoring   │
                       │  (STT/TTS)       │    │  & Analytics    │
                       └──────────────────┘    └─────────────────┘
```

## 🎯 Sales Bot Capabilities

### Lead Qualification
- **Company Size Detection**: Small, medium, or large business
- **Budget Assessment**: Low, medium, or high budget indicators
- **Timeline Analysis**: Immediate, soon, or later implementation
- **Interest Level Tracking**: High, medium, or low engagement

### Intent Recognition
- Greeting and introduction
- Product inquiries
- Pricing questions
- Demo requests
- Objection handling
- Lead qualification
- Conversation closing

### Conversation Management
- Context-aware responses
- Personalized product recommendations
- Natural objection handling
- Automatic lead scoring
- CRM integration for qualified leads

## 🛠️ Quick Start

### 1. Setup

```bash
# Clone the repository
cd voice-streaming/python

# Run the setup script
python setup_sales_bot.py
```

This will:
- Install all dependencies
- Download NLP models
- Create necessary directories
- Set up configuration files

### 2. Configuration

Edit `config.py` to customize your sales bot:

```python
# Sales Bot Configuration
SALES_BOT_NAME = "Sarah"
COMPANY_NAME = "Your Company Name"
PRODUCTS = [
    {"name": "Product 1", "price": "$99/month", "description": "Description"},
    # Add your products here
]

# OpenAI Configuration
OPENAI_API_KEY = "your-openai-api-key-here"
```

### 3. Set Your OpenAI API Key

```bash
# Option 1: Environment variable
export OPENAI_API_KEY="your-api-key-here"

# Option 2: Edit config.py directly
# OPENAI_API_KEY = "your-api-key-here"
```

Get your API key from: https://platform.openai.com/api-keys

### 4. Test the Setup

```bash
python test_sales_bot.py
```

### 5. Run the Sales Bot

```bash
python app.py
```

### 6. Expose with ngrok

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

Use the ngrok URL as your WebSocket endpoint in Exotel.

## 📋 Configuration Options

### Bot Personality
```python
SALES_BOT_NAME = "Sarah"           # Bot's name
COMPANY_NAME = "TechSolutions"     # Your company
TEMPERATURE = 0.7                  # Response creativity (0-1)
```

### Products & Services
```python
PRODUCTS = [
    {
        "name": "CRM Software",
        "price": "$99/month",
        "description": "Complete customer relationship management"
    }
]
```

### Lead Scoring
```python
LEAD_SCORE_FACTORS = {
    "company_size": {"small": 1, "medium": 3, "large": 5},
    "budget": {"low": 1, "medium": 3, "high": 5},
    "timeline": {"immediate": 5, "soon": 3, "later": 1},
    "interest_level": {"high": 5, "medium": 3, "low": 1}
}
```

### Speech Processing
```python
STT_ENGINE = "google"              # Speech-to-text engine
TTS_ENGINE = "gtts"                # Text-to-speech engine
LANGUAGE_CODE = "en-US"            # Language for processing
```

## 🔧 Advanced Features

### CRM Integration

Configure webhook for qualified leads:

```python
CRM_WEBHOOK_URL = "https://your-crm.com/webhook/leads"
```

The bot will automatically send qualified leads to your CRM with:
- Lead contact information
- Conversation summary
- Lead score
- Qualification data

### Conversation Analytics

The bot logs detailed analytics:

```
logs/
├── sales_bot.log          # General application logs
├── calls.log              # Call connection details
├── interactions.log       # Customer-bot interactions
└── conversations.log      # Complete conversation summaries
```

### Slack Notifications

Get notified of hot leads:

```python
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/your/webhook"
```

## 📊 Monitoring & Analytics

### Real-time Logs
```bash
# Monitor live interactions
tail -f logs/interactions.log

# View conversation summaries
tail -f logs/conversations.log

# Check system health
tail -f logs/sales_bot.log
```

### Lead Scoring Dashboard

Each conversation generates:
- **Lead Score**: 0-25 points
- **Qualification Status**: Qualified/Unqualified
- **Contact Information**: Name, email, phone, company
- **Intent Analysis**: Customer goals and interests
- **Sentiment Tracking**: Positive/negative/neutral

## 🎨 Customization

### Custom Responses

Edit response templates in `config.py`:

```python
SALES_RESPONSES = {
    "greeting": "Hi! I'm {bot_name} from {company}. How can I help?",
    "product_overview": "We offer {products}. What interests you?",
    # Customize all responses
}
```

### Intent Classification

Add custom intents:

```python
SALES_INTENTS = {
    "custom_intent": ["keyword1", "keyword2", "phrase"],
    # Add your custom intents
}
```

### Voice Configuration

Customize speech processing:

```python
TTS_LANGUAGE = "en"                # TTS language
VOICE_SPEED = 1.0                  # Speech speed
SAMPLE_RATE = 8000                 # Audio quality
```

## 🔍 Testing

### Unit Tests
```bash
python test_sales_bot.py           # Full test suite
```

### Manual Testing
```bash
python -c "
from sales_bot import SalesBot
bot = SalesBot()
response = bot.process_message('test', 'Hello, I need a CRM solution')
print(response)
"
```

### WebSocket Testing
```bash
python test_connection.py          # Test WebSocket connectivity
```

## 🚀 Deployment

### Local Development
```bash
python app.py                      # Run locally
ngrok http 5000                    # Expose with ngrok
```

### Production Deployment

1. **AWS/GCP/Azure**: Deploy using container services
2. **Domain Setup**: Use proper SSL domain instead of ngrok
3. **Environment Variables**: Store API keys securely
4. **Monitoring**: Set up logging and alerting
5. **Scaling**: Use load balancers for high volume

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

## 🛡️ Security

### API Key Management
- Use environment variables for API keys
- Never commit API keys to version control
- Rotate keys regularly

### WebSocket Security
- Use WSS (secure WebSocket) in production
- Implement authentication if needed
- Rate limiting for abuse prevention

## 📈 Performance Optimization

### Speech Processing
- Buffer audio for better recognition
- Use silence detection to reduce processing
- Implement audio quality enhancement

### Response Generation
- Cache common responses
- Use OpenAI efficiently
- Implement fallback responses

### Lead Management
- Automatic lead deduplication
- Real-time lead scoring updates
- Efficient conversation storage

## 🐛 Troubleshooting

### Common Issues

1. **Speech Recognition Not Working**
   ```bash
   # Check audio dependencies
   pip install pydub[mp3]
   
   # Test Google Speech API
   python -c "import speech_recognition as sr; print('SR working')"
   ```

2. **OpenAI API Errors**
   ```bash
   # Check API key
   echo $OPENAI_API_KEY
   
   # Test connection
   python test_sales_bot.py
   ```

3. **Audio Quality Issues**
   ```python
   # Adjust audio settings in config.py
   SAMPLE_RATE = 16000  # Higher quality
   ```

4. **WebSocket Connection Issues**
   ```bash
   # Check server status
   netstat -an | grep 5000
   
   # Test connectivity
   python test_connection.py
   ```

### Logs Analysis

```bash
# Find errors in logs
grep "ERROR" logs/sales_bot.log

# Check conversation quality
grep "lead_score" logs/interactions.log

# Monitor performance
grep "response_time" logs/sales_bot.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and config examples
- **Issues**: Create GitHub issues for bugs
- **Testing**: Use the test suite to validate functionality
- **Logs**: Check application logs for debugging

---

**Ready to transform your sales process with AI?** 🚀

Get started in minutes:
1. `python setup_sales_bot.py`
2. Add your OpenAI API key
3. `python app.py`
4. Start selling! 📞💼



