# 🚀 Production Voice AI Server

A comprehensive, production-ready WebSocket server for voice streaming with advanced AI capabilities. Built for Exotel integration with multi-engine STT/TTS, intelligent NLP, and real-time analytics.

## 🎯 Features

### 🗣️ **Advanced Speech Processing**
- **Multi-Engine STT**: OpenAI Whisper (primary), Google Speech, Vosk (offline fallback)
- **Multi-Engine TTS**: Google Cloud TTS, gTTS, Coqui TTS, pyttsx3
- **Media Resampling**: 8kHz, 16kHz, 24kHz support with multiple algorithms
- **Real-time Processing**: Low-latency audio processing with silence detection

### 🧠 **Intelligent NLP**
- **LLM Integration**: OpenAI GPT with rule-based fallbacks
- **Intent Recognition**: Advanced customer intent classification
- **Sentiment Analysis**: Real-time emotion and sentiment tracking
- **Entity Extraction**: Contact information and business data capture

### 💼 **Sales Automation**
- **Lead Qualification**: Automatic lead scoring and qualification
- **Conversation Flow**: Context-aware responses and objection handling
- **CRM Integration**: Webhook support for qualified leads
- **Analytics Dashboard**: Real-time call metrics and performance tracking

### 🔧 **Production Features**
- **Scalable Architecture**: Docker deployment with horizontal scaling
- **Event Handling**: Proper clear/mark event support for Exotel
- **Monitoring**: Health checks, metrics, and performance monitoring
- **Security**: Rate limiting, authentication, and data privacy controls

## 📋 Quick Start

### 1. Prerequisites
```bash
# Required
- Python 3.11+
- Docker (for production deployment)
- OpenAI API key

# Optional
- Google Cloud credentials (for enhanced STT/TTS)
- ngrok account (for development)
```

### 2. Installation

#### Development Setup
```bash
# Clone and setup
git clone <repository>
cd voice-streaming/python

# Install dependencies
pip install -r requirements-production.txt

# Download NLP models (optional)
python -m spacy download en_core_web_sm

# Configure environment
cp enhanced_config.py config.py
# Edit config.py with your settings
```

#### Production Docker Setup
```bash
# Create environment file
cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key-here
SALES_BOT_NAME=Sarah
COMPANY_NAME=Your Company Name
EOF

# Deploy with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f voice-ai-server
```

### 3. Configuration

#### Essential Settings
```python
# config.py
OPENAI_API_KEY = "your-openai-api-key-here"
SALES_BOT_NAME = "Sarah"
COMPANY_NAME = "Your Company"

# Your products/services
PRODUCTS = [
    {
        "name": "Your Product",
        "price": "$99/month", 
        "description": "Product description"
    }
]
```

#### Advanced Configuration
```python
# Engine preferences
PRIMARY_STT_PROVIDER = "whisper"  # whisper, google, vosk
PRIMARY_TTS_PROVIDER = "google"   # google, gtts, coqui

# Performance tuning
MAX_CONCURRENT_CALLS = 50
AUDIO_CHUNK_SIZE = 10
SILENCE_THRESHOLD = 0.01

# Features
ENABLE_LEAD_SCORING = True
ENABLE_SENTIMENT_ANALYSIS = True
ENABLE_REAL_TIME_ANALYTICS = True
```

## 🚀 Deployment

### Production Deployment Options

#### 1. Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# Scale WebSocket servers
docker-compose up -d --scale voice-ai-server=3

# View logs
docker-compose logs -f voice-ai-server
```

#### 2. Kubernetes
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-ai-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: voice-ai-server
  template:
    metadata:
      labels:
        app: voice-ai-server
    spec:
      containers:
      - name: voice-ai-server
        image: voice-ai-server:latest
        ports:
        - containerPort: 5000
        - containerPort: 5001
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: voice-ai-secrets
              key: openai-api-key
```

#### 3. Cloud Platforms

##### AWS Deployment
```bash
# AWS ECS with Fargate
aws ecs create-cluster --cluster-name voice-ai-cluster
aws ecs create-service --cluster voice-ai-cluster --service-name voice-ai-service

# AWS Lambda (for serverless)
# Note: Use separate Lambda functions for WebSocket API Gateway integration
```

##### Google Cloud Platform
```bash
# GCP Cloud Run
gcloud run deploy voice-ai-server \
  --image gcr.io/your-project/voice-ai-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

##### Azure Container Instances
```bash
# Azure deployment
az container create \
  --resource-group voice-ai-rg \
  --name voice-ai-server \
  --image voice-ai-server:latest \
  --ports 5000 5001
```

## 🔗 Exotel Integration

### WebSocket Configuration

#### 1. Exotel Settings
```json
{
  "webhook_url": "wss://your-domain.com/",
  "events": ["connected", "start", "media", "clear", "mark", "stop"],
  "media_format": {
    "encoding": "mulaw",
    "sample_rate": 8000,
    "channels": 1
  }
}
```

#### 2. Production URL Setup
```bash
# Option 1: Direct domain (recommended for production)
wss://voice-ai.your-company.com/

# Option 2: ngrok (development/testing)
ngrok http 5000
# Use the ngrok HTTPS URL: wss://abc123.ngrok-free.app/
```

#### 3. Event Handling
The server properly handles all Exotel events:
- **connected**: Call connection established
- **start**: Media streaming started
- **media**: Audio data packets
- **clear**: Clear audio buffer (echo cancellation)
- **mark**: Audio boundary markers
- **stop**: Call ended

### Call Flow Example
```
1. 📞 Customer calls Exotel number
2. 🔗 Exotel connects to your WebSocket server
3. 🎙️ Audio streaming begins
4. 🤖 AI processes speech and responds
5. 💬 Intelligent conversation flow
6. 📊 Lead qualification and scoring
7. 💾 Data saved and CRM integration
8. 📞 Call completion and analytics
```

## 📊 Monitoring & Analytics

### Web Dashboard
Access the dashboard at: `http://your-server:5001`

**Features:**
- 📈 Real-time call metrics
- 🎯 Intent and sentiment analysis
- 👥 Lead qualification tracking
- 🔧 Engine status monitoring
- 📝 Live conversation logs

### REST API Endpoints

#### Metrics
```bash
GET /api/metrics
# Returns server performance metrics

GET /api/calls?limit=50
# Returns recent call summaries

GET /api/interactions?limit=100
# Returns customer interactions

GET /api/leads?qualified=true
# Returns qualified leads

GET /api/analytics?days=7
# Returns analytics for last N days
```

#### Health Check
```bash
GET /api/health
# Returns service health status
```

### Monitoring Integration

#### Prometheus Metrics
```bash
# Enable Prometheus endpoint
ENABLE_PROMETHEUS_METRICS=true

# Metrics available at /metrics
curl http://localhost:5001/metrics
```

#### Grafana Dashboards
Pre-built Grafana dashboards included:
- Call volume and performance
- Engine health and performance
- Lead conversion funnel
- Customer sentiment trends

## 🔧 Advanced Configuration

### Engine Configuration

#### STT Engine Priority
```python
# Primary engine with fallbacks
PRIMARY_STT_PROVIDER = "whisper"  # Best quality
# Fallbacks: google -> vosk (offline)

# Vosk offline model setup
VOSK_MODEL_PATH = "models/vosk-model-en-us-0.22"
```

#### TTS Engine Priority
```python
# High-quality TTS
PRIMARY_TTS_PROVIDER = "google"  # Best quality
# Fallbacks: gtts -> coqui -> pyttsx3

# Voice customization
TTS_VOICE_CONFIG = {
    "google": "en-US-Standard-A",
    "gtts": "en",
    "coqui": "default"
}
```

### Performance Tuning

#### Audio Processing
```python
# Optimize for your use case
AUDIO_CHUNK_SIZE = 10          # Larger = better quality, higher latency
SILENCE_THRESHOLD = 0.01       # Lower = more sensitive
MAX_SILENCE_DURATION = 5.0     # Conversation timeout
RESAMPLER_BACKEND = "scipy"    # Best quality resampling
```

#### Concurrency
```python
# Scale based on your server capacity
MAX_CONCURRENT_CALLS = 50
CALL_TIMEOUT_SECONDS = 1800    # 30 minutes max call time
WEBSOCKET_PING_INTERVAL = 30
```

### Security Configuration

#### Authentication
```python
REQUIRE_AUTH = True
API_KEY = "your-secure-api-key"
RATE_LIMITING_ENABLED = True
MAX_REQUESTS_PER_MINUTE = 100
```

#### Data Privacy
```python
# GDPR/CCPA compliance
DATA_RETENTION_DAYS = 90
ANONYMIZE_LOGS = True
GDPR_COMPLIANCE = True
CONVERSATION_RECORDING = False  # Disable for privacy
```

## 🔗 Integration Guides

### CRM Integration

#### Webhook Setup
```python
# Automatic lead forwarding
CRM_WEBHOOK_URL = "https://your-crm.com/api/leads"
CRM_API_KEY = "your-crm-api-key"
AUTO_CREATE_LEADS = True
```

#### Salesforce Integration
```python
# Salesforce-specific settings
SALESFORCE_INSTANCE_URL = "https://your-instance.salesforce.com"
SALESFORCE_CLIENT_ID = "your-client-id"
SALESFORCE_CLIENT_SECRET = "your-client-secret"
```

#### HubSpot Integration
```python
# HubSpot settings
HUBSPOT_API_KEY = "your-hubspot-api-key"
HUBSPOT_PORTAL_ID = "your-portal-id"
```

### Communication Integration

#### Slack Notifications
```python
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
SLACK_CHANNEL = "#sales-leads"
SLACK_NOTIFY_QUALIFIED_LEADS = True
```

#### Email Notifications
```python
EMAIL_NOTIFICATIONS_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@company.com"
SMTP_PASSWORD = "your-app-password"
```

### Calendar Integration

#### Google Calendar
```python
CALENDAR_API_ENABLED = True
GOOGLE_CALENDAR_CREDENTIALS = "path/to/calendar-credentials.json"
AUTO_SCHEDULE_DEMOS = True
DEFAULT_DEMO_DURATION = 30  # minutes
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Speech Recognition Not Working
```bash
# Check audio dependencies
pip install pydub[mp3]
apt-get install ffmpeg

# Verify STT engines
python -c "from engines.stt_engine import ProductionSTTEngine; print(ProductionSTTEngine().get_provider_status())"
```

#### 2. OpenAI API Errors
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test connection
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### 3. WebSocket Connection Issues
```bash
# Check server status
netstat -an | grep 5000

# Test WebSocket connection
wscat -c ws://localhost:5000
```

#### 4. Docker Issues
```bash
# Check container logs
docker-compose logs voice-ai-server

# Restart services
docker-compose restart

# Rebuild images
docker-compose build --no-cache
```

### Performance Issues

#### High Memory Usage
```python
# Optimize settings
AUDIO_BUFFER_SIZE = 2048      # Reduce buffer size
MAX_CONVERSATION_LENGTH = 15  # Limit conversation history
ENABLE_CONVERSATION_MEMORY = False  # Disable if needed
```

#### High Latency
```python
# Reduce processing time
AUDIO_CHUNK_SIZE = 5          # Process smaller chunks
PREFER_LLM_NLP = False        # Use rule-based NLP
RESAMPLER_BACKEND = "pydub"   # Faster resampling
```

## 📈 Scaling & Load Balancing

### Horizontal Scaling

#### Load Balancer Configuration
```nginx
# nginx.conf
upstream voice_ai_servers {
    server voice-ai-1:5000;
    server voice-ai-2:5000;
    server voice-ai-3:5000;
}

server {
    listen 80;
    server_name voice-ai.your-company.com;
    
    location / {
        proxy_pass http://voice_ai_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

#### Auto-scaling with Kubernetes
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: voice-ai-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: voice-ai-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 🔒 Security Best Practices

### Production Security Checklist
- [ ] Use HTTPS/WSS in production
- [ ] Enable API authentication
- [ ] Configure rate limiting
- [ ] Set up firewall rules
- [ ] Use secure environment variables
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Data encryption at rest

### Environment Variables
```bash
# Never commit these to version control
OPENAI_API_KEY=sk-...
CRM_API_KEY=xxx
DATABASE_PASSWORD=xxx
SLACK_WEBHOOK_URL=https://...
```

## 📞 Support & Documentation

### Getting Help
- 📖 **Documentation**: Check this README and inline code comments
- 🐛 **Issues**: Create GitHub issues for bugs
- 💬 **Discussions**: Use GitHub discussions for questions
- 📧 **Support**: Contact your development team

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

### License
MIT License - see LICENSE file for details.

---

**🚀 Ready to transform your sales process with AI?**

Start with the quick setup above, then customize the configuration for your specific needs. The production server is designed to handle enterprise-scale voice interactions with reliability and intelligence.

For deployment assistance or custom development, contact your technical team. 