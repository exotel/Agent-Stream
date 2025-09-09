# 🤖 Dynamic Bot Framework - Developer Guide

Create and modify AI bots on-the-go for sales, support, service collection, and more!

## 🚀 Quick Start

### 1. Installation & Setup

```bash
cd python/
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Or create a .env file
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 2. Create Your First Bot (Sales Bot)

```python
from bot_framework import BotManager

# Initialize bot manager
bot_manager = BotManager()

# Create a sales bot
config = bot_manager.create_bot(
    bot_type="sales",
    bot_id="my-sales-bot",
    config_overrides={
        "voice": "nova",
        "temperature": 0.8,
        "company_name": "Acme Corp"
    },
    custom_instructions="Focus on our new AI automation services"
)

# Start the bot
await bot_manager.start_bot("my-sales-bot", port=5000)
```

**Your sales bot is now running at:**
- `ws://localhost:5000/?sample-rate=8000` (8kHz)
- `ws://localhost:5000/?sample-rate=16000` (16kHz) 
- `ws://localhost:5000/?sample-rate=24000` (24kHz)

### 3. Test Your Bot

```bash
# Basic test
python test_enhanced_bot.py --server ws://localhost:5000

# Test with 16kHz
python test_enhanced_bot.py --server ws://localhost:5000 --sample-rate 16000

# Interactive testing
python test_enhanced_bot.py --server ws://localhost:5000 --interactive
```

## 🎯 Bot Types & Use Cases

### 🛍️ Sales Bot

**Perfect for:**
- Lead qualification
- Product demos
- Pricing discussions
- Appointment scheduling

```python
sales_bot = bot_manager.create_bot(
    bot_type="sales",
    bot_id="enterprise-sales",
    config_overrides={
        "voice": "nova",          # Enthusiastic voice
        "temperature": 0.7,       # Creative but focused
        "company_name": "TechFlow Solutions",
        "service_description": "Enterprise AI automation"
    },
    custom_instructions="""
    Focus on these key points:
    - Cost savings through automation
    - Improved efficiency metrics
    - Quick ROI (3-6 months)
    - Free consultation offer
    """
)
```

**Available Functions:**
- `schedule_demo()` - Book product demonstrations
- `get_pricing()` - Provide pricing information
- `create_lead()` - Add prospects to CRM
- `transfer_to_human()` - Escalate to human sales rep

### 🎧 Customer Support Bot

**Perfect for:**
- Technical troubleshooting
- Account issues
- FAQ handling
- Ticket creation

```python
support_bot = bot_manager.create_bot(
    bot_type="support",
    bot_id="customer-support",
    config_overrides={
        "voice": "coral",         # Calm, empathetic voice
        "temperature": 0.3,       # Consistent, accurate responses
        "personality": "empathetic"
    },
    custom_instructions="""
    Support priorities:
    1. Listen and acknowledge customer frustration
    2. Gather specific details about the issue
    3. Provide step-by-step solutions
    4. Follow up to ensure resolution
    """
)
```

**Available Functions:**
- `search_knowledge_base()` - Find solutions in KB
- `create_support_ticket()` - Create tickets for complex issues
- `transfer_to_human()` - Escalate to human support

### 💰 Service Collection Bot

**Perfect for:**
- Payment reminders
- Debt collection
- Payment plan setup
- Account reconciliation

```python
collection_bot = bot_manager.create_bot(
    bot_type="service_collection",
    bot_id="payment-collection",
    config_overrides={
        "voice": "echo",          # Professional, authoritative
        "temperature": 0.2,       # Very consistent
        "personality": "professional"
    },
    custom_instructions="""
    Collection approach:
    1. Professional and respectful tone
    2. Clear explanation of outstanding amounts
    3. Offer flexible payment solutions
    4. Document all agreements
    5. Maintain compliance with regulations
    """
)
```

**Available Functions:**
- `get_account_details()` - Retrieve account status
- `setup_payment_plan()` - Create payment arrangements
- `process_payment()` - Handle immediate payments

### 🎯 Lead Generation Bot

**Perfect for:**
- Cold outreach
- Lead qualification
- Market research
- Contact information gathering

```python
lead_gen_bot = bot_manager.create_bot(
    bot_type="lead_generation",
    bot_id="lead-generator",
    config_overrides={
        "voice": "alloy",         # Friendly, approachable
        "temperature": 0.6,       # Conversational
        "personality": "friendly"
    }
)
```

### 📅 Appointment Booking Bot

**Perfect for:**
- Medical appointments
- Consultation scheduling
- Service bookings
- Calendar management

```python
booking_bot = bot_manager.create_bot(
    bot_type="appointment_booking",
    bot_id="appointment-scheduler",
    config_overrides={
        "voice": "shimmer",       # Clear, direct
        "temperature": 0.4,       # Focused on tasks
        "personality": "direct"
    }
)
```

### 📊 Survey/Feedback Bot

**Perfect for:**
- Customer satisfaction surveys
- Market research
- Product feedback
- User experience studies

```python
survey_bot = bot_manager.create_bot(
    bot_type="survey",
    bot_id="feedback-collector",
    config_overrides={
        "voice": "fable",         # Engaging, conversational
        "temperature": 0.5,       # Balanced
        "personality": "casual"
    }
)
```

## 🔧 Advanced Configuration

### Custom Bot from Scratch

```python
from bot_framework import BotConfiguration, BotType, BotPersonality, BotCapabilities

# Create completely custom configuration
custom_config = BotConfiguration(
    bot_id="my-custom-bot",
    bot_name="Custom AI Assistant",
    bot_type=BotType.CUSTOM,
    personality=BotPersonality.PROFESSIONAL,
    
    # AI Settings
    model="gpt-4o-realtime-preview-2024-12-17",
    voice="coral",
    temperature=0.7,
    max_tokens=2000,
    
    # Audio Settings
    sample_rates=[8000, 16000, 24000],
    preferred_sample_rate=16000,
    
    # Capabilities
    capabilities=BotCapabilities(
        can_schedule_appointments=True,
        can_access_knowledge_base=True,
        can_transfer_to_human=True,
        can_send_emails=True,
        custom_functions=["analyze_sentiment", "generate_report"]
    ),
    
    # Instructions
    base_instructions="""You are a specialized AI assistant for...""",
    custom_instructions="""Focus on these specific areas...""",
    
    # Company Info
    company_name="Your Company",
    service_description="Your services",
    contact_info={
        "phone": "+1-555-0123",
        "email": "contact@company.com"
    },
    
    # Custom Tools
    available_tools=[
        {
            "type": "function",
            "name": "custom_function",
            "description": "Your custom function",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                },
                "required": ["input"]
            }
        }
    ]
)

# Save as template for reuse
bot_manager.template_manager.save_template("my-custom-template", custom_config)
```

### Hot-Reload Configuration Changes

```python
# Modify running bot without restart
bot_manager.modify_bot("my-sales-bot", {
    "voice": "shimmer",           # Change voice
    "temperature": 0.9,           # Make more creative
    "custom_instructions": """    # Update instructions
    New focus: Emphasize our latest AI features and 50% discount promotion.
    """
})
# Bot automatically reloads with new configuration!
```

### Configuration from JSON/YAML

Create `my-bot-config.json`:
```json
{
  "bot_id": "json-configured-bot",
  "bot_name": "JSON Configured Assistant",
  "bot_type": "support",
  "personality": "empathetic",
  "voice": "coral",
  "temperature": 0.4,
  "company_name": "Support Corp",
  "base_instructions": "You are an empathetic support representative...",
  "available_tools": [
    {
      "type": "function",
      "name": "resolve_issue",
      "description": "Mark customer issue as resolved",
      "parameters": {
        "type": "object",
        "properties": {
          "issue_id": {"type": "string"},
          "resolution": {"type": "string"}
        },
        "required": ["issue_id", "resolution"]
      }
    }
  ]
}
```

Load and use:
```python
config = bot_manager.create_bot_from_config("my-bot-config.json")
await bot_manager.start_bot("json-configured-bot")
```

## 🎛️ Multi-Bot Management

### Run Multiple Bots Simultaneously

```python
# Create different bots for different purposes
bots_to_create = [
    ("sales", "morning-sales", {"voice": "nova"}, 5001),
    ("support", "24x7-support", {"voice": "coral"}, 5002),
    ("service_collection", "payment-reminder", {"voice": "echo"}, 5003)
]

for bot_type, bot_id, overrides, port in bots_to_create:
    bot_manager.create_bot(bot_type, bot_id, config_overrides=overrides)
    await bot_manager.start_bot(bot_id, port=port)
    print(f"✅ {bot_id} running on port {port}")
```

### Monitor Active Bots

```python
# List all active bots
active_bots = bot_manager.list_active_bots()
for bot_id in active_bots:
    info = bot_manager.get_bot_info(bot_id)
    print(f"🤖 {bot_id}:")
    print(f"   Type: {info['config']['bot_type']}")
    print(f"   Voice: {info['config']['voice']}")
    print(f"   Endpoints: {info['endpoints']}")
```

## 📱 Command Line Interface

The framework includes a powerful CLI for bot management:

### Create Bots

```bash
# Create different types of bots
python bot_framework.py create sales my-sales-bot --voice nova --temperature 0.8
python bot_framework.py create support help-desk --voice coral
python bot_framework.py create service_collection payment-bot --voice echo
```

### Manage Bots

```bash
# List all bots
python bot_framework.py list

# List only active bots
python bot_framework.py list --active-only

# Start a bot
python bot_framework.py start my-sales-bot --port 5001

# Stop a bot
python bot_framework.py stop my-sales-bot

# Modify running bot
python bot_framework.py modify my-sales-bot --voice shimmer --temperature 0.9
```

## 🔄 Real-World Development Workflow

### 1. Rapid Prototyping

```python
# Quick prototype for a restaurant reservation bot
restaurant_bot = bot_manager.create_bot(
    "appointment_booking",
    "restaurant-reservations",
    config_overrides={
        "voice": "fable",
        "company_name": "Bella Vista Restaurant",
        "service_description": "Fine dining reservations"
    },
    custom_instructions="""
    You handle restaurant reservations. Ask for:
    1. Date and time preference
    2. Number of guests
    3. Special requests (dietary restrictions, celebrations)
    4. Contact information
    
    Always confirm details and provide confirmation number.
    """
)

# Test immediately
await bot_manager.start_bot("restaurant-reservations", port=5010)
```

### 2. A/B Testing Different Personalities

```python
# Create two versions for A/B testing
bot_manager.create_bot("sales", "sales-friendly", {
    "personality": "friendly", 
    "voice": "alloy",
    "custom_instructions": "Be warm and conversational"
})

bot_manager.create_bot("sales", "sales-professional", {
    "personality": "professional",
    "voice": "echo", 
    "custom_instructions": "Be direct and business-focused"
})

# Run both and compare performance
await bot_manager.start_bot("sales-friendly", port=5020)
await bot_manager.start_bot("sales-professional", port=5021)
```

### 3. Iterative Improvement

```python
# Start with basic support bot
support_v1 = bot_manager.create_bot("support", "support-v1")
await bot_manager.start_bot("support-v1")

# Test and gather feedback...

# Iterate based on feedback
bot_manager.modify_bot("support-v1", {
    "temperature": 0.2,  # More consistent
    "custom_instructions": """
    Based on user feedback:
    - Always ask clarifying questions
    - Provide step-by-step solutions
    - Offer to create tickets for complex issues
    """
})

# Bot automatically reloads with improvements!
```

## 🔌 Integration Examples

### CRM Integration

```python
# Add CRM integration to any bot
def add_crm_integration(bot_id):
    crm_tools = [
        {
            "type": "function", 
            "name": "create_crm_lead",
            "description": "Create lead in CRM system",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}, 
                    "company": {"type": "string"},
                    "source": {"type": "string"}
                }
            }
        },
        {
            "type": "function",
            "name": "update_contact",
            "description": "Update contact in CRM",
            "parameters": {
                "type": "object", 
                "properties": {
                    "contact_id": {"type": "string"},
                    "updates": {"type": "object"}
                }
            }
        }
    ]
    
    current_config = bot_manager.bot_configs[bot_id]
    current_config.available_tools.extend(crm_tools)
    current_config.capabilities.can_access_crm = True
    
    bot_manager.save_bot_config(bot_id, current_config)

# Apply to sales bot
add_crm_integration("my-sales-bot")
```

### Custom Industry Bot

```python
# Healthcare appointment bot
healthcare_config = {
    "voice": "coral",
    "company_name": "MedCenter Clinic",
    "service_description": "Medical appointments and consultations",
    "custom_instructions": """
    You schedule medical appointments. Important guidelines:
    
    HIPAA Compliance:
    - Never ask for or discuss specific medical conditions
    - Don't provide medical advice
    - Keep conversations focused on scheduling
    
    Required Information:
    - Patient name and DOB
    - Insurance information  
    - Preferred doctor/specialty
    - Appointment type (routine, urgent, follow-up)
    - Preferred date/time
    
    Always verify insurance coverage and provide appointment confirmation.
    """
}

healthcare_bot = bot_manager.create_bot(
    "appointment_booking",
    "healthcare-scheduler", 
    config_overrides=healthcare_config
)
```

## 📊 Analytics & Monitoring

### Bot Performance Tracking

```python
# Get bot analytics
def get_bot_analytics(bot_id):
    info = bot_manager.get_bot_info(bot_id)
    
    # In production, you'd query your analytics database
    analytics = {
        "total_conversations": 1234,
        "avg_conversation_length": "3.2 minutes",
        "successful_outcomes": "78%",
        "common_intents": ["pricing", "demo", "support"],
        "user_satisfaction": 4.2
    }
    
    return analytics

# Monitor all active bots
for bot_id in bot_manager.list_active_bots():
    analytics = get_bot_analytics(bot_id)
    print(f"📊 {bot_id} Analytics: {analytics}")
```

## 🚀 Deployment Strategies

### Production Deployment

```python
# Production-ready multi-bot setup
production_bots = [
    {
        "type": "sales", 
        "id": "sales-primary",
        "port": 8001,
        "config": {"voice": "nova", "temperature": 0.7}
    },
    {
        "type": "sales",
        "id": "sales-backup", 
        "port": 8002,
        "config": {"voice": "nova", "temperature": 0.7}
    },
    {
        "type": "support",
        "id": "support-24x7",
        "port": 8003, 
        "config": {"voice": "coral", "temperature": 0.3}
    }
]

async def deploy_production():
    for bot_config in production_bots:
        bot_manager.create_bot(
            bot_config["type"],
            bot_config["id"],
            config_overrides=bot_config["config"]
        )
        await bot_manager.start_bot(
            bot_config["id"], 
            host="0.0.0.0",
            port=bot_config["port"]
        )
        print(f"🚀 Deployed {bot_config['id']} on port {bot_config['port']}")

# Deploy all bots
await deploy_production()
```

### Load Balancing Setup

```nginx
# nginx.conf for load balancing multiple bot instances
upstream sales_bots {
    server localhost:8001;
    server localhost:8002;
}

upstream support_bots {
    server localhost:8003;
    server localhost:8004;
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

## 🎯 Best Practices

### 1. Configuration Management

```python
# Use environment-specific configs
environments = {
    "development": {
        "voice": "alloy",
        "temperature": 0.8,  # More creative for testing
        "log_level": "DEBUG"
    },
    "staging": {
        "voice": "coral", 
        "temperature": 0.7,
        "log_level": "INFO"
    },
    "production": {
        "voice": "nova",
        "temperature": 0.6,  # More consistent
        "log_level": "WARNING"
    }
}

current_env = os.getenv("ENVIRONMENT", "development")
env_config = environments[current_env]

bot_manager.create_bot("sales", "env-specific-bot", config_overrides=env_config)
```

### 2. Template Reuse

```python
# Create reusable industry templates
industries = {
    "healthcare": {
        "voice": "coral",
        "personality": "empathetic",
        "temperature": 0.3,
        "instructions": "Focus on HIPAA compliance and patient care"
    },
    "finance": {
        "voice": "echo",
        "personality": "professional", 
        "temperature": 0.2,
        "instructions": "Emphasize security and regulatory compliance"
    },
    "retail": {
        "voice": "fable",
        "personality": "friendly",
        "temperature": 0.6, 
        "instructions": "Focus on customer satisfaction and sales"
    }
}

# Create industry-specific bots quickly
for industry, config in industries.items():
    bot_id = f"{industry}-sales-bot"
    bot_manager.create_bot("sales", bot_id, config_overrides=config)
```

### 3. Error Handling & Fallbacks

```python
# Robust bot creation with fallbacks
def create_robust_bot(bot_type, bot_id, primary_config, fallback_config=None):
    try:
        return bot_manager.create_bot(bot_type, bot_id, config_overrides=primary_config)
    except Exception as e:
        logger.warning(f"Primary config failed: {e}")
        if fallback_config:
            logger.info("Trying fallback configuration")
            return bot_manager.create_bot(bot_type, bot_id, config_overrides=fallback_config)
        raise

# Use with fallback
primary_config = {"voice": "nova", "temperature": 0.8}
fallback_config = {"voice": "alloy", "temperature": 0.7}

robust_bot = create_robust_bot("sales", "robust-sales", primary_config, fallback_config)
```

## 🔮 Advanced Features

### Dynamic Function Loading

```python
# Load custom functions at runtime
def load_custom_functions(bot_id, functions_module):
    """Load custom functions from a Python module"""
    spec = importlib.util.spec_from_file_location("custom_functions", functions_module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get all callable functions
    functions = [
        {
            "name": name,
            "function": func,
            "description": func.__doc__ or f"Custom function: {name}"
        }
        for name, func in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith('_')
    ]
    
    # Add to bot configuration
    config = bot_manager.bot_configs[bot_id]
    config.capabilities.custom_functions.extend([f["name"] for f in functions])
    
    return functions

# Load custom functions for a specific industry
custom_functions = load_custom_functions("my-bot", "industry_specific_functions.py")
```

### Multi-Language Support

```python
# Create multi-language bots
languages = {
    "english": {"voice": "nova", "instructions": "Respond in English"},
    "spanish": {"voice": "nova", "instructions": "Respond in Spanish (Responder en español)"},
    "french": {"voice": "shimmer", "instructions": "Respond in French (Répondre en français)"}
}

for lang, config in languages.items():
    bot_id = f"support-{lang}"
    bot_manager.create_bot("support", bot_id, config_overrides=config)
    await bot_manager.start_bot(bot_id, port=5000 + hash(lang) % 1000)
```

This framework gives you complete flexibility to create, modify, and manage AI bots for any use case. The hot-reload capability means you can iterate quickly and deploy changes without downtime!

## 🛠️ Quick Reference Commands

```bash
# Framework CLI
python bot_framework.py create sales my-bot --voice nova
python bot_framework.py start my-bot --port 5001
python bot_framework.py modify my-bot --temperature 0.8
python bot_framework.py list --active-only

# Testing
python test_enhanced_bot.py --server ws://localhost:5001 --sample-rate 16000

# Production startup
./start_enhanced_bot.sh
```

Ready to build amazing AI bots? Start with the examples above and customize for your specific needs! 🚀 