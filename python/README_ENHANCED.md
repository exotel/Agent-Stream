# 🚀 Enhanced OpenAI Realtime Sales Bot Framework

> **Create, customize, and deploy AI bots for any use case in minutes!**

This enhanced framework transforms the original sales bot into a powerful, flexible platform that supports multiple bot types, multi-sample rate audio processing, hot-reloading, and dynamic configuration changes.

## ✨ What's New in the Enhanced Version

### 🎵 **Multi-Sample Rate Support**
- **8kHz, 16kHz, 24kHz** support for better Exotel integration
- **Automatic sample rate detection** from WebSocket URL parameters
- **Dynamic audio quality optimization** based on connection

### 📦 **Variable Chunk Processing**
- **Minimum 20ms chunks** as per Exotel specifications
- **Dynamic chunk sizing** based on network conditions
- **Enhanced mark/clear event handling** for better interruption support

### 🤖 **Multiple Bot Types**
Create specialized bots for different use cases:
- 🛍️ **Sales & Lead Generation**
- 🎧 **Customer Support** 
- 💰 **Service Collection/Debt Recovery**
- 📅 **Appointment Booking**
- 📊 **Survey & Feedback Collection**
- ⚙️ **Custom Configurations**

### 🔄 **Hot-Reload Capabilities**
- **Real-time configuration changes** without restarting
- **File-watching system** for automatic updates
- **Zero-downtime modifications**

### 🎛️ **Advanced Management**
- **Multi-bot management** - run multiple bots simultaneously
- **Template system** for quick bot creation
- **Import/Export** configurations
- **Interactive CLI** for easy management

## 🚀 Quick Start

### 1. **Universal Bot Launcher (Recommended)**

```bash
# Interactive bot creation and management
python bot_launcher.py --interactive

# Run demo scenarios
python bot_launcher.py --demo

# Quick start guide
python bot_launcher.py --quick-start
```

### 2. **Direct Bot Creation**

```python
from bot_framework import BotManager

# Initialize manager
bot_manager = BotManager()

# Create a sales bot
sales_bot = bot_manager.create_bot(
    bot_type="sales",
    bot_id="my-sales-bot",
    config_overrides={
        "voice": "nova",
        "temperature": 0.8,
        "company_name": "Acme Corp"
    }
)

# Start the bot
await bot_manager.start_bot("my-sales-bot", port=5000)
```

### 3. **Traditional Enhanced Bot**

```bash
# Start with enhanced features
./start_enhanced_bot.sh

# Test multi-sample rates
python test_enhanced_bot.py --sample-rate 16000 --comprehensive
```

## 🎯 Bot Types & Use Cases

### 🛍️ Sales & Lead Generation Bot
Perfect for converting prospects into customers.

```python
sales_bot = bot_manager.create_bot(
    "sales", 
    "enterprise-sales",
    {
        "voice": "nova",
        "personality": "enthusiastic", 
        "company_name": "TechFlow Solutions",
        "temperature": 0.7
    },
    custom_instructions="Focus on enterprise AI solutions with ROI benefits"
)
```

**Use Cases:**
- Lead qualification calls
- Product demonstrations
- Pricing discussions
- Appointment scheduling
- Objection handling

### 🎧 Customer Support Bot
Empathetic support for existing customers.

```python
support_bot = bot_manager.create_bot(
    "support",
    "24x7-support", 
    {
        "voice": "coral",
        "personality": "empathetic",
        "temperature": 0.3  # More consistent responses
    }
)
```

**Use Cases:**
- Technical troubleshooting
- Account issues
- Order tracking
- Return processing
- FAQ handling

### 💰 Service Collection Bot
Professional debt recovery and payment reminders.

```python
collection_bot = bot_manager.create_bot(
    "service_collection",
    "payment-collection",
    {
        "voice": "echo",
        "personality": "professional",
        "temperature": 0.2  # Very consistent
    }
)
```

**Use Cases:**
- Payment reminders
- Debt collection calls
- Payment plan setup
- Account reconciliation
- Compliance management

### 📅 Appointment Booking Bot
Efficient scheduling and calendar management.

```python
booking_bot = bot_manager.create_bot(
    "appointment_booking",
    "medical-scheduler",
    {
        "voice": "shimmer",
        "personality": "direct",
        "company_name": "MedCenter Clinic"
    }
)
```

**Use Cases:**
- Medical appointments
- Consultation scheduling
- Service bookings
- Calendar management
- Availability checking

## 🔧 Advanced Features

### 🔄 Hot-Reload Configuration

```python
# Modify running bot without restart
bot_manager.modify_bot("my-sales-bot", {
    "voice": "shimmer",
    "temperature": 0.9,
    "custom_instructions": "New promotion: 50% off this week!"
})
# Changes applied instantly! 🚀
```

### 🌐 Multi-Bot Management

```python
# Run multiple specialized bots
bots = [
    ("sales", "morning-sales", {"voice": "nova"}, 5001),
    ("support", "24x7-support", {"voice": "coral"}, 5002),
    ("service_collection", "collections", {"voice": "echo"}, 5003)
]

for bot_type, bot_id, config, port in bots:
    bot_manager.create_bot(bot_type, bot_id, config_overrides=config)
    await bot_manager.start_bot(bot_id, port=port)
```

### 📊 Real-Time Analytics

```python
# Monitor all active bots
for bot_id in bot_manager.list_active_bots():
    info = bot_manager.get_bot_info(bot_id)
    print(f"🤖 {bot_id}: {info['config']['bot_type']} on port {info['port']}")
    print(f"   Endpoints: {info['endpoints']}")
```

## 🎵 Multi-Sample Rate Support

### Exotel Integration

Your bots now support Exotel's enhanced upsampling/downsampling features:

```
# Enhanced Exotel WebSocket URLs
wss://yourdomain.ai/media?sample-rate=8000   # Traditional telephony
wss://yourdomain.ai/media?sample-rate=16000  # High quality
wss://yourdomain.ai/media?sample-rate=24000  # Premium quality
```

### Automatic Detection

The bot automatically detects and optimizes for the sample rate:

```python
# Sample rate is detected from URL automatically
# Audio processing adapts accordingly
# OpenAI format selection optimized (G.711 vs PCM16)
```

### Testing Different Sample Rates

```bash
# Test 8kHz (traditional)
python test_enhanced_bot.py --sample-rate 8000

# Test 16kHz (high quality)  
python test_enhanced_bot.py --sample-rate 16000

# Test 24kHz (premium quality)
python test_enhanced_bot.py --sample-rate 24000

# Comprehensive testing
python test_enhanced_bot.py --comprehensive
```

## 🎪 Demo Scenarios

### 1. Restaurant Reservation System

```bash
cd examples/
python restaurant_bot.py
```

Creates a specialized restaurant reservation bot with:
- Menu knowledge and recommendations
- Availability checking
- Special occasion handling
- Dietary restriction support
- Confirmation system

### 2. E-Commerce Support System

```bash
cd examples/
python ecommerce_support_bot.py
```

Creates a complete e-commerce support system with 3 specialized bots:
- **General Support** (Port 5020) - Orders, returns, account issues
- **Sales Support** (Port 5021) - Product recommendations, deals
- **Technical Support** (Port 5022) - Setup help, troubleshooting

### 3. Hot-Reload Demonstration

```bash
cd examples/
python ecommerce_support_bot.py --hot-reload-demo
```

Shows real-time configuration changes without restarting bots.

## 📋 Configuration Options

### Bot Personalities

```python
personalities = {
    "professional": "Business-focused, direct communication",
    "friendly": "Warm, approachable, conversational", 
    "casual": "Relaxed, informal tone",
    "empathetic": "Understanding, supportive, patient",
    "direct": "Efficient, straight to the point",
    "enthusiastic": "Energetic, positive, engaging"
}
```

### Voice Options

```python
voices = {
    "alloy": "Balanced, versatile voice",
    "echo": "Professional, authoritative", 
    "fable": "Engaging, storytelling quality",
    "onyx": "Deep, confident tone",
    "nova": "Energetic, enthusiastic",
    "shimmer": "Clear, direct communication",
    "coral": "Calm, empathetic (new enhanced voice)"
}
```

### Audio Configuration

```python
# Enhanced audio settings
audio_config = {
    "sample_rates": [8000, 16000, 24000],
    "min_chunk_size_ms": 20,      # Exotel minimum
    "buffer_size_ms": 160,        # Optimal latency
    "dynamic_chunk_sizing": True,  # Adaptive chunks
    "audio_enhancement": True      # Noise suppression
}
```

## 🛠️ CLI Commands

### Bot Framework CLI

```bash
# Create different types of bots
python bot_framework.py create sales my-bot --voice nova --temperature 0.8
python bot_framework.py create support help-desk --voice coral

# Manage bots
python bot_framework.py list --active-only
python bot_framework.py start my-bot --port 5001
python bot_framework.py stop my-bot

# Modify running bots
python bot_framework.py modify my-bot --voice shimmer --temperature 0.9
```

### Testing Commands

```bash
# Basic testing
python test_enhanced_bot.py --server ws://localhost:5001

# Interactive testing
python test_enhanced_bot.py --server ws://localhost:5001 --interactive

# Sample rate testing
python test_enhanced_bot.py --server ws://localhost:5001 --sample-rate 16000

# Comprehensive test suite
python test_enhanced_bot.py --comprehensive
```

### Universal Launcher

```bash
# Interactive mode (recommended for beginners)
python bot_launcher.py --interactive

# Demo scenarios
python bot_launcher.py --demo

# Quick help
python bot_launcher.py --quick-start
```

## 📁 Project Structure

```
python/
├── 🤖 Core Framework
│   ├── bot_framework.py              # Dynamic bot framework
│   ├── openai_realtime_sales_bot.py  # Enhanced base bot
│   ├── config.py                     # Enhanced configuration
│   └── bot_launcher.py               # Universal launcher
│
├── 🔧 Engines & Processing  
│   ├── engines/
│   │   ├── media_resampler.py        # Multi-sample rate support
│   │   ├── audio_enhancer.py         # Audio enhancement
│   │   ├── stt_engine.py            # Speech-to-text
│   │   ├── tts_engine.py            # Text-to-speech
│   │   └── nlp_engine.py            # NLP processing
│
├── 🧪 Testing & Examples
│   ├── test_enhanced_bot.py          # Comprehensive testing
│   ├── examples/
│   │   ├── restaurant_bot.py         # Restaurant reservation
│   │   └── ecommerce_support_bot.py  # E-commerce support
│
├── 📋 Templates & Configuration
│   ├── bot_templates/               # Bot templates
│   ├── active_bots/                # Active bot configs
│   └── requirements.txt            # Enhanced dependencies
│
└── 📚 Documentation
    ├── README_ENHANCED.md          # This file
    ├── DEVELOPER_GUIDE.md          # Detailed dev guide
    └── EXOTEL_ENDPOINTS.md         # Exotel integration
```

## 🔌 Integration Examples

### CRM Integration

```python
# Add CRM capabilities to any bot
bot_manager.modify_bot("sales-bot", {
    "capabilities": {
        "can_access_crm": True,
        "can_create_leads": True,
        "can_update_contacts": True
    }
})
```

### Custom Industry Bot

```python
# Healthcare appointment bot
healthcare_bot = bot_manager.create_bot(
    "appointment_booking",
    "medical-scheduler",
    {
        "voice": "coral",
        "company_name": "MedCenter Clinic",
        "custom_instructions": """
        HIPAA Compliance Guidelines:
        - Never discuss specific medical conditions
        - Focus only on scheduling
        - Verify insurance information
        - Confirm appointment details
        """
    }
)
```

### Multi-Language Support

```python
# Create bots for different languages
languages = {
    "english": {"voice": "nova", "instructions": "Respond in English"},
    "spanish": {"voice": "nova", "instructions": "Respond in Spanish (Responder en español)"}
}

for lang, config in languages.items():
    bot_manager.create_bot("support", f"support-{lang}", config_overrides=config)
```

## 🚀 Production Deployment

### Docker Deployment

```bash
# Build enhanced image
docker build -t enhanced-ai-bots .

# Run with multi-port support
docker run -p 5000-5010:5000-5010 enhanced-ai-bots
```

### Environment Configuration

```bash
# Enhanced environment variables
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-realtime-preview-2024-12-17"
export OPENAI_VOICE="coral"

# Multi-sample rate settings
export SAMPLE_RATE="16000"
export MIN_CHUNK_SIZE_MS="20"
export DYNAMIC_CHUNK_SIZING="true"

# Enhanced features
export EXOTEL_MARK_CLEAR_ENHANCED="true"
export AUDIO_ENHANCEMENT_ENABLED="true"
```

### Load Balancing

```nginx
# nginx configuration for multiple bot instances
upstream sales_bots {
    server localhost:5001;
    server localhost:5002;
}

upstream support_bots {
    server localhost:5003;
    server localhost:5004;
}

server {
    listen 80;
    
    location /sales/ {
        proxy_pass http://sales_bots;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /support/ {
        proxy_pass http://support_bots;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📊 Monitoring & Analytics

### Bot Performance Tracking

```python
# Monitor bot performance
def get_bot_analytics(bot_id):
    return {
        "total_conversations": 1234,
        "avg_conversation_length": "3.2 minutes", 
        "success_rate": "78%",
        "user_satisfaction": 4.2,
        "common_intents": ["pricing", "demo", "support"]
    }

# Real-time monitoring
for bot_id in bot_manager.list_active_bots():
    analytics = get_bot_analytics(bot_id)
    logger.info(f"📊 {bot_id}: {analytics}")
```

### Health Checks

```python
# Built-in health checking
async def health_check():
    active_bots = bot_manager.list_active_bots()
    healthy_bots = []
    
    for bot_id in active_bots:
        try:
            info = bot_manager.get_bot_info(bot_id)
            if info.get("active"):
                healthy_bots.append(bot_id)
        except Exception:
            pass
    
    return {
        "status": "healthy" if healthy_bots else "unhealthy",
        "active_bots": len(healthy_bots),
        "total_bots": len(active_bots)
    }
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **Sample Rate Not Detected**
```bash
# Check WebSocket URL format
# ✅ Correct: ws://localhost:5000/?sample-rate=16000
# ❌ Wrong: ws://localhost:5000/sample-rate=16000
```

#### 2. **Bot Not Hot-Reloading**
```python
# Ensure file watcher is running
bot_manager = BotManager()  # File watcher starts automatically
```

#### 3. **Audio Quality Issues**
```python
# Enable audio enhancement
bot_manager.modify_bot("bot-id", {
    "audio_enhancement_enabled": True,
    "noise_threshold": 1000
})
```

#### 4. **Port Already in Use**
```bash
# Kill existing processes
lsof -ti:5000 | xargs kill -9

# Or use auto-port selection
await bot_manager.start_bot("bot-id")  # Auto-assigns port
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"
export VERBOSE_LOGGING="true"

# Run with debug
python bot_launcher.py --interactive
```

## 🤝 Contributing

### Adding New Bot Types

1. **Create Template**
   ```python
   def _create_my_bot_template(self) -> BotConfiguration:
       return BotConfiguration(
           bot_type=BotType.CUSTOM,
           personality=BotPersonality.PROFESSIONAL,
           # ... configuration
       )
   ```

2. **Add to Template Manager**
   ```python
   templates["my_bot"] = self._create_my_bot_template()
   ```

3. **Test Implementation**
   ```bash
   python bot_framework.py create my_bot test-bot
   python test_enhanced_bot.py --server ws://localhost:PORT
   ```

### Extending Audio Processing

```python
# Add custom audio processing
class CustomAudioProcessor:
    def process_audio(self, audio_data: bytes, sample_rate: int) -> bytes:
        # Your custom processing
        return processed_audio

# Integrate with bot
bot.add_audio_processor(CustomAudioProcessor())
```

## 🎓 Learning Path

### Beginner (5 minutes)
1. Run `python bot_launcher.py --interactive`
2. Create your first sales bot
3. Test with `test_enhanced_bot.py --interactive`

### Intermediate (30 minutes)
1. Create multiple bot types
2. Try hot-reload modifications
3. Run e-commerce demo system
4. Test different sample rates

### Advanced (2 hours)
1. Create custom bot configurations
2. Set up multi-bot production system
3. Implement custom functions
4. Add monitoring and analytics

### Expert (Full Day)
1. Build industry-specific bot templates
2. Implement custom audio processing
3. Create load-balanced deployment
4. Add comprehensive testing suite

## 🔗 API Reference

### BotManager Methods

```python
# Core methods
create_bot(bot_type, bot_id, config_overrides=None, custom_instructions=None)
start_bot(bot_id, host="0.0.0.0", port=None)
stop_bot(bot_id)
modify_bot(bot_id, modifications, save=True)

# Information
list_active_bots() -> List[str]
list_available_bots() -> List[str] 
get_bot_info(bot_id) -> Dict[str, Any]

# Import/Export
export_bot(bot_id, export_path)
import_bot(import_path, new_bot_id=None)

# Template management
bot_manager.template_manager.get_template(name)
bot_manager.template_manager.save_template(name, config)
```

### Configuration Options

```python
class BotConfiguration:
    # Core
    bot_id: str
    bot_type: BotType  
    personality: BotPersonality
    
    # AI
    model: str = "gpt-4o-realtime-preview-2024-12-17"
    voice: str = "coral"
    temperature: float = 0.7
    
    # Audio  
    sample_rates: List[int] = [8000, 16000, 24000]
    preferred_sample_rate: int = 16000
    
    # Company
    company_name: str = "Your Company"
    service_description: str = "Professional services"
    
    # Instructions
    base_instructions: str = ""
    custom_instructions: str = ""
```

## 📞 Support & Community

- **Documentation**: See `DEVELOPER_GUIDE.md` for detailed examples
- **Issues**: Report bugs and request features
- **Examples**: Check `examples/` directory for real-world use cases
- **Testing**: Use `test_enhanced_bot.py` for comprehensive testing

---

## 🎯 Ready to Build Amazing AI Bots?

Start with the interactive launcher:

```bash
python bot_launcher.py --interactive
```

Or jump straight into creating a specialized bot:

```python
from bot_framework import BotManager

bot_manager = BotManager()

# Your first enhanced AI bot in 3 lines!
config = bot_manager.create_bot("sales", "my-amazing-bot")
await bot_manager.start_bot("my-amazing-bot")
print("🚀 Bot ready for Exotel integration!")
```

**Happy bot building!** 🤖✨ 