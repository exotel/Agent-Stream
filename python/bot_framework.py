#!/usr/bin/env python3
"""
Dynamic Bot Framework - Create and modify bots on-the-go
Supports sales, support, service collection, and custom bot types with hot-reloading

Usage Examples:
    # Sales Bot
    bot_manager = BotManager()
    bot_manager.create_bot("sales", "my-sales-bot", config_overrides={"voice": "nova"})
    
    # Support Bot
    bot_manager.create_bot("support", "customer-support", config_overrides={"temperature": 0.3})
    
    # Custom Bot from JSON
    bot_manager.create_bot_from_config("custom-bot.json")
"""

import asyncio
import json
import logging
import os
import time
import importlib.util
import inspect
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import Config

logger = logging.getLogger(__name__)

class BotType(Enum):
    """Supported bot types"""
    SALES = "sales"
    SUPPORT = "support"
    SERVICE_COLLECTION = "service_collection"
    LEAD_GENERATION = "lead_generation"
    APPOINTMENT_BOOKING = "appointment_booking"
    SURVEY = "survey"
    CUSTOM = "custom"

class BotPersonality(Enum):
    """Bot personality types"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    EMPATHETIC = "empathetic"
    DIRECT = "direct"
    ENTHUSIASTIC = "enthusiastic"

@dataclass
class BotCapabilities:
    """Bot capabilities configuration"""
    can_schedule_appointments: bool = False
    can_access_knowledge_base: bool = False
    can_transfer_to_human: bool = True
    can_collect_payments: bool = False
    can_send_emails: bool = False
    can_make_outbound_calls: bool = False
    can_access_crm: bool = False
    can_process_forms: bool = False
    custom_functions: List[str] = field(default_factory=list)

@dataclass
class BotConfiguration:
    """Complete bot configuration"""
    # Basic Info
    bot_id: str
    bot_name: str
    bot_type: BotType
    personality: BotPersonality = BotPersonality.PROFESSIONAL
    
    # AI Configuration
    model: str = "gpt-4o-realtime-preview-2024-12-17"
    voice: str = "coral"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # Audio Settings
    sample_rates: List[int] = field(default_factory=lambda: [8000, 16000, 24000])
    preferred_sample_rate: int = 16000
    
    # Capabilities
    capabilities: BotCapabilities = field(default_factory=BotCapabilities)
    
    # Custom Instructions
    base_instructions: str = ""
    custom_instructions: str = ""
    conversation_starters: List[str] = field(default_factory=list)
    
    # Company/Service Info
    company_name: str = "Your Company"
    service_description: str = "Professional services"
    contact_info: Dict[str, str] = field(default_factory=dict)
    
    # Tools/Functions
    available_tools: List[Dict[str, Any]] = field(default_factory=list)
    
    # Advanced Settings
    interruption_threshold: float = 0.5
    response_delay_ms: int = 200
    max_conversation_turns: int = 50
    auto_end_conversation: bool = False
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: str = "1.0.0"

class BotTemplateManager:
    """Manages bot templates for different use cases"""
    
    def __init__(self):
        self.templates_dir = Path("bot_templates")
        self.templates_dir.mkdir(exist_ok=True)
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default bot templates"""
        templates = {
            "sales": self._create_sales_template(),
            "support": self._create_support_template(),
            "service_collection": self._create_service_collection_template(),
            "lead_generation": self._create_lead_generation_template(),
            "appointment_booking": self._create_appointment_booking_template(),
            "survey": self._create_survey_template()
        }
        
        for template_name, template in templates.items():
            template_file = self.templates_dir / f"{template_name}.json"
            if not template_file.exists():
                with open(template_file, 'w') as f:
                    json.dump(self._config_to_dict(template), f, indent=2)
                logger.info(f"Created template: {template_name}")
    
    def _create_sales_template(self) -> BotConfiguration:
        """Create sales bot template"""
        return BotConfiguration(
            bot_id="sales-template",
            bot_name="AI Sales Assistant",
            bot_type=BotType.SALES,
            personality=BotPersonality.ENTHUSIASTIC,
            temperature=0.7,
            voice="nova",
            capabilities=BotCapabilities(
                can_schedule_appointments=True,
                can_access_knowledge_base=True,
                can_transfer_to_human=True,
                can_send_emails=True,
                can_access_crm=True
            ),
            base_instructions="""You are an enthusiastic AI sales representative. Your goals are to:
1. Build rapport with potential customers
2. Understand their needs and pain points
3. Present relevant solutions
4. Handle objections professionally
5. Guide towards next steps (demo, trial, purchase)

Always be helpful, never pushy. Focus on solving customer problems.""",
            conversation_starters=[
                "Hi! Thanks for your interest in our solutions. How can I help you today?",
                "Hello! I'm here to help you find the perfect solution for your needs. What brings you here?",
                "Welcome! I'd love to learn more about your business and see how we can help. What's your biggest challenge right now?"
            ],
            available_tools=[
                {
                    "type": "function",
                    "name": "schedule_demo",
                    "description": "Schedule a product demonstration",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string"},
                            "company": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                            "product_interest": {"type": "string"},
                            "preferred_date": {"type": "string"},
                            "preferred_time": {"type": "string"}
                        },
                        "required": ["customer_name", "email", "product_interest"]
                    }
                },
                {
                    "type": "function",
                    "name": "get_pricing",
                    "description": "Get pricing information for products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product": {"type": "string"},
                            "company_size": {"type": "string"},
                            "use_case": {"type": "string"}
                        },
                        "required": ["product"]
                    }
                },
                {
                    "type": "function",
                    "name": "create_lead",
                    "description": "Create a new sales lead in CRM",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_info": {"type": "object"},
                            "interest_level": {"type": "string"},
                            "notes": {"type": "string"},
                            "next_action": {"type": "string"}
                        },
                        "required": ["contact_info"]
                    }
                }
            ]
        )
    
    def _create_support_template(self) -> BotConfiguration:
        """Create customer support bot template"""
        return BotConfiguration(
            bot_id="support-template",
            bot_name="AI Customer Support",
            bot_type=BotType.SUPPORT,
            personality=BotPersonality.EMPATHETIC,
            temperature=0.3,  # More consistent responses
            voice="coral",
            capabilities=BotCapabilities(
                can_access_knowledge_base=True,
                can_transfer_to_human=True,
                can_access_crm=True,
                can_send_emails=True,
                can_process_forms=True
            ),
            base_instructions="""You are a patient and helpful customer support representative. Your goals are to:
1. Listen carefully to customer issues
2. Show empathy and understanding
3. Provide accurate solutions quickly
4. Escalate when necessary
5. Follow up to ensure satisfaction

Always remain calm and professional, even with frustrated customers.""",
            conversation_starters=[
                "Hi! I'm here to help resolve any issues you might have. What can I assist you with today?",
                "Hello! Sorry to hear you're having trouble. Let me help you get this sorted out right away.",
                "Welcome to support! I'm here to make sure we resolve your concern quickly. What's going on?"
            ],
            available_tools=[
                {
                    "type": "function",
                    "name": "search_knowledge_base",
                    "description": "Search the knowledge base for solutions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "category": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "type": "function",
                    "name": "create_support_ticket",
                    "description": "Create a support ticket for complex issues",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string"},
                            "issue_description": {"type": "string"},
                            "priority": {"type": "string"},
                            "category": {"type": "string"}
                        },
                        "required": ["issue_description"]
                    }
                },
                {
                    "type": "function",
                    "name": "transfer_to_human",
                    "description": "Transfer to human support agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string"},
                            "context": {"type": "string"},
                            "urgency": {"type": "string"}
                        },
                        "required": ["reason"]
                    }
                }
            ]
        )
    
    def _create_service_collection_template(self) -> BotConfiguration:
        """Create service collection/debt recovery bot template"""
        return BotConfiguration(
            bot_id="service-collection-template",
            bot_name="AI Service Collection Assistant",
            bot_type=BotType.SERVICE_COLLECTION,
            personality=BotPersonality.PROFESSIONAL,
            temperature=0.2,  # Very consistent
            voice="echo",
            capabilities=BotCapabilities(
                can_collect_payments=True,
                can_access_crm=True,
                can_send_emails=True,
                can_process_forms=True,
                can_transfer_to_human=True
            ),
            base_instructions="""You are a professional service collection assistant. Your goals are to:
1. Approach customers with respect and professionalism
2. Clearly explain outstanding obligations
3. Offer flexible payment solutions
4. Document all interactions properly
5. Maintain compliance with regulations

Always be firm but fair, and focus on finding mutually beneficial solutions.""",
            conversation_starters=[
                "Hello, I'm calling regarding your account. I'd like to work with you to resolve this matter.",
                "Hi, this is about your outstanding service obligation. Let's find a solution that works for both of us.",
                "Good day, I'm reaching out to discuss your account status and see how we can help."
            ],
            available_tools=[
                {
                    "type": "function",
                    "name": "get_account_details",
                    "description": "Retrieve account and payment details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_number": {"type": "string"},
                            "customer_id": {"type": "string"}
                        },
                        "required": ["account_number"]
                    }
                },
                {
                    "type": "function",
                    "name": "setup_payment_plan",
                    "description": "Set up a payment plan for the customer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_number": {"type": "string"},
                            "payment_amount": {"type": "number"},
                            "payment_frequency": {"type": "string"},
                            "start_date": {"type": "string"}
                        },
                        "required": ["account_number", "payment_amount"]
                    }
                },
                {
                    "type": "function",
                    "name": "process_payment",
                    "description": "Process immediate payment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_number": {"type": "string"},
                            "payment_method": {"type": "string"},
                            "amount": {"type": "number"}
                        },
                        "required": ["account_number", "amount"]
                    }
                }
            ]
        )
    
    def _create_lead_generation_template(self) -> BotConfiguration:
        """Create lead generation bot template"""
        return BotConfiguration(
            bot_id="lead-generation-template",
            bot_name="AI Lead Generation Assistant",
            bot_type=BotType.LEAD_GENERATION,
            personality=BotPersonality.FRIENDLY,
            temperature=0.6,
            voice="alloy",
            capabilities=BotCapabilities(
                can_access_knowledge_base=True,
                can_send_emails=True,
                can_access_crm=True,
                can_process_forms=True,
                can_schedule_appointments=True
            ),
            base_instructions="""You are a friendly lead generation specialist. Your goals are to:
1. Engage prospects in natural conversation
2. Qualify leads based on specific criteria
3. Gather contact and business information
4. Identify pain points and opportunities
5. Schedule follow-up actions

Focus on building relationships and understanding prospect needs.""",
            conversation_starters=[
                "Hi! I noticed you might be interested in improving your business operations. Is that right?",
                "Hello! I'd love to learn more about your business and see if we might be a good fit to work together.",
                "Hi there! I help businesses like yours solve common challenges. What's your biggest pain point right now?"
            ]
        )
    
    def _create_appointment_booking_template(self) -> BotConfiguration:
        """Create appointment booking bot template"""
        return BotConfiguration(
            bot_id="appointment-booking-template",
            bot_name="AI Appointment Booking Assistant",
            bot_type=BotType.APPOINTMENT_BOOKING,
            personality=BotPersonality.DIRECT,
            temperature=0.4,
            voice="shimmer",
            capabilities=BotCapabilities(
                can_schedule_appointments=True,
                can_access_crm=True,
                can_send_emails=True,
                can_process_forms=True
            ),
            base_instructions="""You are an efficient appointment booking assistant. Your goals are to:
1. Quickly understand the appointment type needed
2. Check availability and offer options
3. Collect necessary information
4. Confirm appointment details
5. Send confirmation and reminders

Be direct and efficient while remaining friendly and helpful."""
        )
    
    def _create_survey_template(self) -> BotConfiguration:
        """Create survey/feedback bot template"""
        return BotConfiguration(
            bot_id="survey-template",
            bot_name="AI Survey Assistant",
            bot_type=BotType.SURVEY,
            personality=BotPersonality.CASUAL,
            temperature=0.5,
            voice="fable",
            capabilities=BotCapabilities(
                can_process_forms=True,
                can_send_emails=True
            ),
            base_instructions="""You are a casual survey assistant. Your goals are to:
1. Make surveys feel conversational, not interrogative
2. Adapt questions based on previous answers
3. Encourage honest feedback
4. Keep participants engaged
5. Thank them for their time

Make the experience enjoyable and valuable for participants."""
        )
    
    def get_template(self, template_name: str) -> Optional[BotConfiguration]:
        """Get a bot template by name"""
        template_file = self.templates_dir / f"{template_name}.json"
        if template_file.exists():
            with open(template_file, 'r') as f:
                template_data = json.load(f)
            return self._dict_to_config(template_data)
        return None
    
    def save_template(self, template_name: str, config: BotConfiguration):
        """Save a bot configuration as a template"""
        template_file = self.templates_dir / f"{template_name}.json"
        with open(template_file, 'w') as f:
            json.dump(self._config_to_dict(config), f, indent=2)
        logger.info(f"Saved template: {template_name}")
    
    def list_templates(self) -> List[str]:
        """List available templates"""
        return [f.stem for f in self.templates_dir.glob("*.json")]
    
    def _config_to_dict(self, config: BotConfiguration) -> Dict[str, Any]:
        """Convert BotConfiguration to dictionary"""
        result = {}
        for field_name in config.__dataclass_fields__:
            value = getattr(config, field_name)
            if isinstance(value, Enum):
                result[field_name] = value.value
            elif hasattr(value, '__dataclass_fields__'):
                result[field_name] = self._config_to_dict(value)
            else:
                result[field_name] = value
        return result
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BotConfiguration:
        """Convert dictionary to BotConfiguration"""
        # Convert enum strings back to enums
        if 'bot_type' in data:
            data['bot_type'] = BotType(data['bot_type'])
        if 'personality' in data:
            data['personality'] = BotPersonality(data['personality'])
        
        # Handle capabilities
        if 'capabilities' in data:
            data['capabilities'] = BotCapabilities(**data['capabilities'])
        
        return BotConfiguration(**data)

class ConfigurationWatcher(FileSystemEventHandler):
    """Watches for configuration file changes and reloads bots"""
    
    def __init__(self, bot_manager):
        self.bot_manager = bot_manager
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            bot_id = Path(event.src_path).stem
            if bot_id in self.bot_manager.active_bots:
                logger.info(f"🔄 Reloading bot configuration: {bot_id}")
                asyncio.create_task(self.bot_manager.reload_bot(bot_id))

class BotManager:
    """Manages multiple bot instances with hot-reloading capabilities"""
    
    def __init__(self):
        self.active_bots: Dict[str, Any] = {}
        self.bot_configs: Dict[str, BotConfiguration] = {}
        self.template_manager = BotTemplateManager()
        
        # Set up configuration directories
        self.bots_dir = Path("active_bots")
        self.bots_dir.mkdir(exist_ok=True)
        
        # Set up file watching for hot-reload
        self.observer = Observer()
        self.observer.schedule(
            ConfigurationWatcher(self),
            str(self.bots_dir),
            recursive=False
        )
        self.observer.start()
        
        logger.info("🤖 Bot Manager initialized with hot-reload capability")
    
    def create_bot(
        self, 
        bot_type: str, 
        bot_id: str, 
        config_overrides: Optional[Dict[str, Any]] = None,
        custom_instructions: Optional[str] = None
    ) -> BotConfiguration:
        """Create a new bot from template"""
        
        # Get base template
        template = self.template_manager.get_template(bot_type)
        if not template:
            raise ValueError(f"Unknown bot type: {bot_type}")
        
        # Create new configuration
        config = BotConfiguration(
            **self.template_manager._config_to_dict(template)
        )
        config.bot_id = bot_id
        config.updated_at = time.time()
        
        # Apply overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Add custom instructions
        if custom_instructions:
            config.custom_instructions = custom_instructions
        
        # Save configuration
        self.save_bot_config(bot_id, config)
        
        # Register bot
        self.bot_configs[bot_id] = config
        
        logger.info(f"✅ Created {bot_type} bot: {bot_id}")
        return config
    
    def create_bot_from_config(self, config_file: str) -> BotConfiguration:
        """Create bot from JSON/YAML configuration file"""
        config_path = Path(config_file)
        
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            with open(config_path, 'r') as f:
                data = json.load(f)
        
        config = self.template_manager._dict_to_config(data)
        bot_id = config.bot_id
        
        self.save_bot_config(bot_id, config)
        self.bot_configs[bot_id] = config
        
        logger.info(f"✅ Created bot from config: {bot_id}")
        return config
    
    def modify_bot(
        self, 
        bot_id: str, 
        modifications: Dict[str, Any],
        save: bool = True
    ) -> BotConfiguration:
        """Modify an existing bot configuration"""
        if bot_id not in self.bot_configs:
            raise ValueError(f"Bot not found: {bot_id}")
        
        config = self.bot_configs[bot_id]
        
        # Apply modifications
        for key, value in modifications.items():
            if hasattr(config, key):
                setattr(config, key, value)
                logger.info(f"Modified {bot_id}.{key} = {value}")
        
        config.updated_at = time.time()
        
        if save:
            self.save_bot_config(bot_id, config)
        
        # Hot-reload if bot is active
        if bot_id in self.active_bots:
            asyncio.create_task(self.reload_bot(bot_id))
        
        return config
    
    def save_bot_config(self, bot_id: str, config: BotConfiguration):
        """Save bot configuration to file"""
        config_file = self.bots_dir / f"{bot_id}.json"
        with open(config_file, 'w') as f:
            json.dump(self.template_manager._config_to_dict(config), f, indent=2)
    
    def load_bot_config(self, bot_id: str) -> Optional[BotConfiguration]:
        """Load bot configuration from file"""
        config_file = self.bots_dir / f"{bot_id}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
            return self.template_manager._dict_to_config(data)
        return None
    
    async def start_bot(self, bot_id: str, host: str = "0.0.0.0", port: int = None):
        """Start a bot server"""
        config = self.bot_configs.get(bot_id)
        if not config:
            config = self.load_bot_config(bot_id)
            if not config:
                raise ValueError(f"Bot configuration not found: {bot_id}")
            self.bot_configs[bot_id] = config
        
        # Use config-specific port or auto-assign
        if port is None:
            port = 5000 + len(self.active_bots)
        
        # Import and create the enhanced bot class
        from openai_realtime_sales_bot import OpenAIRealtimeSalesBot
        
        # Create bot instance with configuration
        bot_instance = DynamicBot(config)
        
        # Store active bot
        self.active_bots[bot_id] = {
            "instance": bot_instance,
            "config": config,
            "host": host,
            "port": port,
            "server_task": None
        }
        
        # Start WebSocket server
        import websockets
        server_coro = websockets.serve(
            bot_instance.handle_websocket,
            host,
            port
        )
        
        server_task = asyncio.create_task(server_coro)
        self.active_bots[bot_id]["server_task"] = server_task
        
        logger.info(f"🚀 Started bot {bot_id} on {host}:{port}")
        
        # Print WebSocket endpoints
        logger.info(f"📞 WebSocket endpoints for {bot_id}:")
        for rate in config.sample_rates:
            logger.info(f"   • ws://{host}:{port}/?sample-rate={rate}")
        
        return server_task
    
    async def stop_bot(self, bot_id: str):
        """Stop a running bot"""
        if bot_id in self.active_bots:
            bot_info = self.active_bots[bot_id]
            if bot_info["server_task"]:
                bot_info["server_task"].cancel()
            del self.active_bots[bot_id]
            logger.info(f"🛑 Stopped bot: {bot_id}")
    
    async def reload_bot(self, bot_id: str):
        """Hot-reload a bot with new configuration"""
        if bot_id not in self.active_bots:
            logger.warning(f"Bot not active: {bot_id}")
            return
        
        # Load new configuration
        new_config = self.load_bot_config(bot_id)
        if not new_config:
            logger.error(f"Failed to load config for: {bot_id}")
            return
        
        # Update bot instance
        bot_info = self.active_bots[bot_id]
        bot_info["instance"].update_configuration(new_config)
        bot_info["config"] = new_config
        self.bot_configs[bot_id] = new_config
        
        logger.info(f"🔄 Hot-reloaded bot: {bot_id}")
    
    def list_active_bots(self) -> List[str]:
        """List currently active bots"""
        return list(self.active_bots.keys())
    
    def list_available_bots(self) -> List[str]:
        """List available bot configurations"""
        return [f.stem for f in self.bots_dir.glob("*.json")]
    
    def get_bot_info(self, bot_id: str) -> Dict[str, Any]:
        """Get information about a bot"""
        info = {}
        
        if bot_id in self.bot_configs:
            config = self.bot_configs[bot_id]
            info["config"] = {
                "bot_type": config.bot_type.value,
                "personality": config.personality.value,
                "voice": config.voice,
                "capabilities": [
                    attr for attr in dir(config.capabilities)
                    if not attr.startswith('_') and getattr(config.capabilities, attr)
                ]
            }
        
        if bot_id in self.active_bots:
            bot_info = self.active_bots[bot_id]
            info["active"] = True
            info["host"] = bot_info["host"]
            info["port"] = bot_info["port"]
            info["endpoints"] = [
                f"ws://{bot_info['host']}:{bot_info['port']}/?sample-rate={rate}"
                for rate in bot_info["config"].sample_rates
            ]
        else:
            info["active"] = False
        
        return info
    
    def export_bot(self, bot_id: str, export_path: str):
        """Export bot configuration for sharing"""
        config = self.bot_configs.get(bot_id)
        if not config:
            raise ValueError(f"Bot not found: {bot_id}")
        
        export_data = {
            "version": "1.0",
            "exported_at": time.time(),
            "bot_config": self.template_manager._config_to_dict(config)
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"📤 Exported bot {bot_id} to {export_path}")
    
    def import_bot(self, import_path: str, new_bot_id: str = None):
        """Import bot configuration from export file"""
        with open(import_path, 'r') as f:
            export_data = json.load(f)
        
        config = self.template_manager._dict_to_config(export_data["bot_config"])
        
        if new_bot_id:
            config.bot_id = new_bot_id
        
        bot_id = config.bot_id
        self.save_bot_config(bot_id, config)
        self.bot_configs[bot_id] = config
        
        logger.info(f"📥 Imported bot: {bot_id}")
        return config
    
    def shutdown(self):
        """Shutdown bot manager"""
        self.observer.stop()
        self.observer.join()

class DynamicBot:
    """Dynamic bot that can be reconfigured on-the-fly"""
    
    def __init__(self, config: BotConfiguration):
        self.config = config
        self.connections = {}
        
        # Import the enhanced sales bot functionality
        from openai_realtime_sales_bot import OpenAIRealtimeSalesBot
        self.bot_class = OpenAIRealtimeSalesBot
        
        logger.info(f"🤖 Created dynamic bot: {config.bot_id}")
    
    def update_configuration(self, new_config: BotConfiguration):
        """Update bot configuration at runtime"""
        old_config = self.config
        self.config = new_config
        
        logger.info(f"🔄 Updated configuration for {new_config.bot_id}")
        
        # Log significant changes
        if old_config.voice != new_config.voice:
            logger.info(f"   Voice: {old_config.voice} → {new_config.voice}")
        if old_config.temperature != new_config.temperature:
            logger.info(f"   Temperature: {old_config.temperature} → {new_config.temperature}")
        if old_config.personality != new_config.personality:
            logger.info(f"   Personality: {old_config.personality.value} → {new_config.personality.value}")
    
    async def handle_websocket(self, websocket, path=None):
        """Handle WebSocket connections with dynamic configuration"""
        # Create a temporary enhanced bot instance with current config
        temp_bot = self.bot_class()
        
        # Override configuration
        temp_bot.openai_voice = self.config.voice
        temp_bot.openai_model = self.config.model
        
        # Handle connection
        await temp_bot.handle_exotel_websocket(websocket, path)

# CLI Interface for bot management
def create_cli_interface():
    """Create command-line interface for bot management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dynamic Bot Framework CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create bot
    create_parser = subparsers.add_parser('create', help='Create a new bot')
    create_parser.add_argument('bot_type', choices=[bt.value for bt in BotType])
    create_parser.add_argument('bot_id', help='Unique bot identifier')
    create_parser.add_argument('--voice', help='Voice to use')
    create_parser.add_argument('--temperature', type=float, help='AI temperature')
    create_parser.add_argument('--custom-instructions', help='Custom instructions')
    
    # List bots
    list_parser = subparsers.add_parser('list', help='List bots')
    list_parser.add_argument('--active-only', action='store_true', help='Show only active bots')
    
    # Start bot
    start_parser = subparsers.add_parser('start', help='Start a bot')
    start_parser.add_argument('bot_id', help='Bot to start')
    start_parser.add_argument('--port', type=int, help='Port to run on')
    
    # Stop bot
    stop_parser = subparsers.add_parser('stop', help='Stop a bot')
    stop_parser.add_argument('bot_id', help='Bot to stop')
    
    # Modify bot
    modify_parser = subparsers.add_parser('modify', help='Modify bot configuration')
    modify_parser.add_argument('bot_id', help='Bot to modify')
    modify_parser.add_argument('--voice', help='Change voice')
    modify_parser.add_argument('--temperature', type=float, help='Change temperature')
    modify_parser.add_argument('--instructions', help='Change instructions')
    
    return parser

async def cli_main():
    """CLI main function"""
    parser = create_cli_interface()
    args = parser.parse_args()
    
    bot_manager = BotManager()
    
    try:
        if args.command == 'create':
            overrides = {}
            if args.voice:
                overrides['voice'] = args.voice
            if args.temperature is not None:
                overrides['temperature'] = args.temperature
            
            bot_manager.create_bot(
                args.bot_type,
                args.bot_id,
                config_overrides=overrides,
                custom_instructions=args.custom_instructions
            )
            print(f"✅ Created {args.bot_type} bot: {args.bot_id}")
            
        elif args.command == 'list':
            if args.active_only:
                bots = bot_manager.list_active_bots()
                print("Active bots:")
            else:
                bots = bot_manager.list_available_bots()
                print("Available bots:")
            
            for bot_id in bots:
                info = bot_manager.get_bot_info(bot_id)
                status = "🟢 ACTIVE" if info.get("active") else "⚪ INACTIVE"
                bot_type = info.get("config", {}).get("bot_type", "unknown")
                print(f"  {status} {bot_id} ({bot_type})")
                if info.get("endpoints"):
                    for endpoint in info["endpoints"]:
                        print(f"    📞 {endpoint}")
            
        elif args.command == 'start':
            await bot_manager.start_bot(args.bot_id, port=args.port)
            print(f"🚀 Started bot: {args.bot_id}")
            
        elif args.command == 'stop':
            await bot_manager.stop_bot(args.bot_id)
            print(f"🛑 Stopped bot: {args.bot_id}")
            
        elif args.command == 'modify':
            modifications = {}
            if args.voice:
                modifications['voice'] = args.voice
            if args.temperature is not None:
                modifications['temperature'] = args.temperature
            if args.instructions:
                modifications['custom_instructions'] = args.instructions
            
            bot_manager.modify_bot(args.bot_id, modifications)
            print(f"🔄 Modified bot: {args.bot_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        bot_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(cli_main()) 