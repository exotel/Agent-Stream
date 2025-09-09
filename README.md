# OpenAI Realtime Bot Framework - Production Ready

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Production Ready](https://img.shields.io/badge/status-production--ready-green.svg)]()

A production-ready WebSocket bot framework that integrates with OpenAI's Realtime API for high-quality voice conversations. Optimized for Exotel telephony

## Features

- **Multi-Sample Rate Support**: 8kHz, 16kHz, 24kHz audio processing
- **Adaptive Chunk Sizing**: 20ms-200ms chunks for optimal performance
- **High-Quality Audio**: 24kHz processing with automatic upsampling
- **Production Architecture**: Scalable, secure, and monitored
- **Multiple Bot Types**: Sales, Support, Qualification, Collection bots
- **Telephony Integration**: Ready for Exotel
- **Real-time Processing**: Low-latency voice conversations
- **Robust Error Handling**: Comprehensive logging and monitoring
- **Docker Support**: Containerized deployment ready
- **Kubernetes Ready**: Scalable orchestration support

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Bot Types](#bot-types)
- [Deployment](#deployment)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd production-ready
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
export OPENAI_API_KEY="your_openai_api_key"
export COMPANY_NAME="Your Company Name"
export ASSISTANT_NAME="Sarah"
```

### 3. Start Basic Bot

```bash
# Start the basic realtime bot
python src/core/realtime_bot.py

# Or start a specialized bot
python src/examples/sales_bot.py
```

### 4. Test Connection

```bash
# Install wscat for testing
npm install -g wscat

# Test WebSocket connection
wscat -c 'ws://localhost:5000/?sample-rate=24000'
```

## Architecture

### High-Level Architecture

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Telephony │ │ OpenAI │ │ Your │
│ Provider │◄──►│ Realtime Bot │◄──►│ Business │
│ (Exotel) │ │ Framework │ │ Logic │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Audio Processing Flow

```
PSTN Call (8kHz) → Telephony Provider → Upsampling → Bot (24kHz) → OpenAI (24kHz)
 ↓
Response (24kHz) ← Telephony Provider ← Downsampling ← OpenAI Response
```

### Key Components

1. **Core Bot Framework** (`src/core/realtime_bot.py`)
 - WebSocket connection management
 - OpenAI Realtime API integration
 - Audio stream processing
 - Error handling and recovery

2. **Configuration System** (`src/config/settings.py`)
 - Environment-based configuration
 - Multi-environment support
 - Security best practices

3. **Specialized Bots** (`src/examples/`)
 - Sales Bot: Lead generation and qualification
 - Support Bot: Customer service and issue resolution
 - Qualification Bot: Lead scoring and routing
 - Collection Bot: Payment and account management

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API key with Realtime API access
- Telephony provider account (Exotel)
- ngrok or similar tunneling service (for development)

### Development Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Setup pre-commit hooks
pre-commit install

# 5. Run tests
pytest tests/
```

### Production Setup

```bash
# 1. Install production dependencies only
pip install -r requirements.txt --no-dev

# 2. Setup environment variables
export OPENAI_API_KEY="your_key"
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="5000"
export LOG_LEVEL="INFO"

# 3. Run with production server
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.core.realtime_bot:app
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-realtime-preview-2024-12-17` | |
| `OPENAI_VOICE` | Voice for responses | `coral` | |
| `SERVER_HOST` | Host to bind server | `0.0.0.0` | |
| `SERVER_PORT` | Port to bind server | `5000` | |
| `DEFAULT_SAMPLE_RATE` | Default audio sample rate | `24000` | |
| `MAX_CHUNK_SIZE_MS` | Maximum chunk size | `200` | |
| `COMPANY_NAME` | Your company name | `Your AI Company` | |
| `ASSISTANT_NAME` | Assistant name | `Sarah` | |

### Audio Configuration

```bash
# Sample rates (Hz)
export DEFAULT_SAMPLE_RATE=24000 # High quality
# Supported: 8000, 16000, 24000

# Chunk sizing (milliseconds)
export MIN_CHUNK_SIZE_MS=20 # Low latency
export MAX_CHUNK_SIZE_MS=200 # High quality
export BUFFER_SIZE_MS=50 # Standard buffer

# Audio enhancement
export AUDIO_ENHANCEMENT_ENABLED=true
export DYNAMIC_CHUNK_SIZING=true
```

### Production Configuration

```bash
# Security
export ALLOWED_ORIGINS="https://yourdomain.com"
export MAX_CONNECTIONS=100
export CONNECTION_TIMEOUT=300

# Performance
export WORKER_PROCESSES=4
export MAX_MESSAGE_SIZE=1048576

# Monitoring
export HEALTH_CHECK_ENABLED=true
export METRICS_ENABLED=true
export SENTRY_DSN="your_sentry_dsn"
```

## Bot Types

### Sales Bot

Optimized for lead generation and sales conversations.

```bash
# Environment setup
export BOT_TYPE="sales"
export PRODUCTS="AI Solutions,Voice Bots,Customer Service"

# Start sales bot
python src/examples/sales_bot.py
```

**Features:**
- BANT qualification (Budget, Authority, Need, Timeline)
- Objection handling
- Product knowledge integration
- CRM integration ready
- Follow-up scheduling

### Support Bot

Designed for customer service and issue resolution.

```bash
# Environment setup
export BOT_TYPE="support"
export SUPPORT_CATEGORIES="Technical,Billing,Account,General"
export ESCALATION_THRESHOLD=3

# Start support bot
python src/examples/support_bot.py
```

**Features:**
- Issue diagnosis and troubleshooting
- Knowledge base integration
- Escalation management
- Customer satisfaction tracking
- Ticket creation

### Qualification Bot

Specialized for lead scoring and routing.

```bash
# Environment setup
export BOT_TYPE="qualification"
export QUALIFICATION_CRITERIA="budget,authority,need,timeline"

# Start qualification bot
python src/examples/qualification_bot.py
```

### Collection Bot

Focused on payment and account management.

```bash
# Environment setup
export BOT_TYPE="collection"
export PAYMENT_METHODS="card,bank,upi"

# Start collection bot
python src/examples/collection_bot.py
```

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY logs/ ./logs/

EXPOSE 5000
CMD ["python", "src/core/realtime_bot.py"]
```

```bash
# Build and run
docker build -t openai-realtime-bot .
docker run -p 5000:5000 -e OPENAI_API_KEY="your_key" openai-realtime-bot
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
 bot:
 build: .
 ports:
 - "5000:5000"
 environment:
 - OPENAI_API_KEY=${OPENAI_API_KEY}
 - COMPANY_NAME=${COMPANY_NAME}
 volumes:
 - ./logs:/app/logs
 restart: unless-stopped

 redis:
 image: redis:7-alpine
 ports:
 - "6379:6379"

 postgres:
 image: postgres:15-alpine
 environment:
 - POSTGRES_DB=botdb
 - POSTGRES_USER=botuser
 - POSTGRES_PASSWORD=botpass
 volumes:
 - postgres_data:/var/lib/postgresql/data

volumes:
 postgres_data:
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: openai-realtime-bot
spec:
 replicas: 3
 selector:
 matchLabels:
 app: openai-realtime-bot
 template:
 metadata:
 labels:
 app: openai-realtime-bot
 spec:
 containers:
 - name: bot
 image: openai-realtime-bot:latest
 ports:
 - containerPort: 5000
 env:
 - name: OPENAI_API_KEY
 valueFrom:
 secretKeyRef:
 name: bot-secrets
 key: openai-api-key
 resources:
 requests:
 memory: "256Mi"
 cpu: "250m"
 limits:
 memory: "512Mi"
 cpu: "500m"
```

### Cloud Deployment

#### AWS ECS

```bash
# Create ECS task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create ECS service
aws ecs create-service --cluster bot-cluster --service-name realtime-bot --task-definition bot-task
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/openai-realtime-bot
gcloud run deploy --image gcr.io/PROJECT-ID/openai-realtime-bot --platform managed
```

#### Azure Container Instances

```bash
# Deploy to Azure
az container create --resource-group myResourceGroup --name openai-bot --image openai-realtime-bot:latest
```

## Scaling

### Horizontal Scaling

```bash
# Multiple instances with load balancer
docker-compose up --scale bot=3

# Kubernetes horizontal pod autoscaler
kubectl autoscale deployment openai-realtime-bot --cpu-percent=70 --min=2 --max=10
```

### Performance Optimization

1. **Connection Pooling**
 ```python
 # Configure connection limits
 MAX_CONNECTIONS = 100
 CONNECTION_TIMEOUT = 300
 ```

2. **Memory Management**
 ```python
 # Audio buffer optimization
 MAX_CHUNK_SIZE_MS = 200 # Larger chunks for efficiency
 DYNAMIC_CHUNK_SIZING = True
 ```

3. **Load Balancing**
 ```nginx
 # nginx.conf
 upstream bot_backend {
 server bot1:5000;
 server bot2:5000;
 server bot3:5000;
 }
 ```

### Database Scaling

```python
# Connection pooling
DATABASE_URL = "postgresql://user:pass@localhost/db?pool_size=20&max_overflow=30"

# Redis caching
REDIS_URL = "redis://localhost:6379/0"
CACHE_TTL = 3600 # 1 hour
```

## Monitoring

### Health Checks

```python
# Health check endpoint
@app.get("/health")
async def health_check():
 return {
 "status": "healthy",
 "timestamp": datetime.utcnow(),
 "connections": len(bot.connections),
 "openai_status": "connected"
 }
```

### Metrics Collection

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

CALL_COUNTER = Counter('bot_calls_total', 'Total number of calls')
CALL_DURATION = Histogram('bot_call_duration_seconds', 'Call duration')
ACTIVE_CONNECTIONS = Gauge('bot_active_connections', 'Active connections')
```

### Logging

```python
# Structured logging
import structlog

logger = structlog.get_logger()
logger.info("Call started", 
 stream_id=stream_id, 
 sample_rate=sample_rate,
 customer_id=customer_id)
```

### Error Tracking

```python
# Sentry integration
import sentry_sdk

sentry_sdk.init(
 dsn="your_sentry_dsn",
 traces_sample_rate=1.0
)
```

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Errors

**Problem**: `'ServerConnection' object has no attribute 'path'`

**Solution**: Update websockets library compatibility
```python
# Fixed in realtime_bot.py
websocket_path = path or getattr(websocket, 'path', '/') or '/'
```

#### 2. OpenAI API Errors

**Problem**: `Invalid modalities: ['audio']`

**Solution**: Use correct modalities
```python
"modalities": ["audio", "text"] # Not just ["audio"]
```

#### 3. Audio Quality Issues

**Problem**: "Ghost voice" or "talking too fast"

**Solution**: Ensure proper sample rate architecture
```python
# OpenAI always at 24kHz, provider handles upsampling
DEFAULT_SAMPLE_RATE = 24000
```

#### 4. Memory Issues

**Problem**: High memory usage with long calls

**Solution**: Optimize chunk sizes and cleanup
```python
MAX_CHUNK_SIZE_MS = 200 # Larger chunks
# Proper cleanup in _cleanup_connection()
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG_AUDIO=true
export DEBUG_WEBSOCKETS=true

# Run with debug
python src/core/realtime_bot.py --debug
```

### Performance Profiling

```bash
# Profile memory usage
pip install memory-profiler
python -m memory_profiler src/core/realtime_bot.py

# Profile CPU usage
pip install py-spy
py-spy record -o profile.svg -- python src/core/realtime_bot.py
```

## Best Practices

### Security

1. **Environment Variables**
 ```bash
 # Never commit API keys
 echo "OPENAI_API_KEY=sk-..." >> .env
 echo ".env" >> .gitignore
 ```

2. **Input Validation**
 ```python
 # Validate all inputs
 def validate_sample_rate(rate: int) -> int:
 if rate not in SUPPORTED_SAMPLE_RATES:
 raise ValueError(f"Unsupported sample rate: {rate}")
 return rate
 ```

3. **Rate Limiting**
 ```python
 # Implement rate limiting
 from slowapi import Limiter
 limiter = Limiter(key_func=get_remote_address)

 @limiter.limit("10/minute")
 async def websocket_endpoint():
 pass
 ```

### Performance

1. **Connection Management**
 ```python
 # Proper connection cleanup
 async def _cleanup_connection(self, stream_id: str):
 # Close OpenAI connection
 # Clean up memory
 # Log session data
 ```

2. **Audio Optimization**
 ```python
 # Adaptive chunk sizing
 def get_adaptive_chunk_size(sample_rate: int) -> int:
 if sample_rate >= 24000:
 return 200 # ms
 elif sample_rate >= 16000:
 return 50 # ms
 else:
 return 20 # ms
 ```

3. **Memory Management**
 ```python
 # Limit concurrent connections
 MAX_CONNECTIONS = 100

 # Use connection pooling
 # Implement proper garbage collection
 ```

### Code Quality

1. **Type Hints**
 ```python
 from typing import Dict, List, Optional, Any

 async def handle_message(self, data: Dict[str, Any]) -> None:
 pass
 ```

2. **Error Handling**
 ```python
 try:
 await process_audio(audio_data)
 except AudioProcessingError as e:
 logger.error(f"Audio processing failed: {e}")
 await send_error_response(stream_id, "audio_error")
 except Exception as e:
 logger.exception(f"Unexpected error: {e}")
 await cleanup_connection(stream_id)
 ```

3. **Testing**
 ```python
 # Unit tests
 @pytest.mark.asyncio
 async def test_websocket_connection():
 bot = OpenAIRealtimeBot()
 # Test connection logic

 # Integration tests
 async def test_full_conversation_flow():
 # Test end-to-end conversation
 ```

### Deployment

1. **Environment Management**
 ```bash
 # Use different configs per environment
 .env.development
 .env.staging
 .env.production
 ```

2. **Health Checks**
 ```python
 # Implement comprehensive health checks
 async def health_check():
 checks = {
 "database": await check_database(),
 "openai": await check_openai_api(),
 "redis": await check_redis()
 }
 return {"status": "healthy", "checks": checks}
 ```

3. **Graceful Shutdown**
 ```python
 # Handle shutdown signals
 import signal

 def signal_handler(signum, frame):
 logger.info("Shutting down gracefully...")
 # Close all connections
 # Save session data
 sys.exit(0)

 signal.signal(signal.SIGTERM, signal_handler)
 ```

## API Reference

### Core Bot Class

```python
class OpenAIRealtimeBot:
 """Production-ready OpenAI Realtime Bot."""

 def __init__(self):
 """Initialize bot with configuration."""

 async def handle_websocket_connection(self, websocket, path=None):
 """Handle incoming WebSocket connections."""

 async def start_server(self):
 """Start the WebSocket server."""
```

### Configuration Class

```python
class Config:
 """Configuration management."""

 @classmethod
 def get_session_config(cls, sample_rate: int, voice: str, bot_type: str) -> Dict[str, Any]:
 """Get OpenAI session configuration."""

 @classmethod
 def validate_config(cls) -> bool:
 """Validate configuration settings."""
```

### WebSocket Events

| Event | Description | Handler |
|-------|-------------|---------|
| `connected` | Connection established | `handle_connected_event()` |
| `start` | Call started | `handle_start_event()` |
| `media` | Audio data received | `handle_media_event()` |
| `mark` | Audio synchronization | `handle_mark_event()` |
| `clear` | Clear audio buffer | `handle_clear_event()` |
| `stop` | Call ended | `handle_stop_event()` |

## Contributing

### Development Workflow

1. **Fork and Clone**
 ```bash
 git clone https://github.com/yourusername/openai-realtime-bot.git
 cd openai-realtime-bot
 ```

2. **Create Branch**
 ```bash
 git checkout -b feature/your-feature-name
 ```

3. **Make Changes**
 ```bash
 # Follow code style guidelines
 black src/
 flake8 src/
 mypy src/
 ```

4. **Test Changes**
 ```bash
 pytest tests/ -v --cov=src/
 ```

5. **Submit PR**
 ```bash
 git push origin feature/your-feature-name
 # Create pull request on GitHub
 ```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Add unit tests
- Update documentation

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ --cov-report=html

# Run specific test
pytest tests/test_realtime_bot.py::test_websocket_connection
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the Realtime API
- Exotel for telephony integration support
- The open-source community for various libraries used

## Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/openai-realtime-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/openai-realtime-bot/discussions)
- **Email**: support@yourcompany.com

---

**Made with ❤️ by the Agent Stream Team** 
