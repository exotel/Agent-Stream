#!/usr/bin/env python3
"""
Exotel AgentStream - Configuration Settings
===========================================

Copyright (c) 2025 Exotel Techcom Pvt. Ltd.
Licensed under the MIT License.

Centralized configuration management for the Exotel AgentStream OpenAI integration.
All settings are loaded from environment variables with sensible defaults.

Environment Variables:
- OPENAI_API_KEY: Your OpenAI API key (required)
- OPENAI_MODEL: OpenAI model to use (default: gpt-4o-realtime-preview-2024-12-17)
- OPENAI_VOICE: Voice for responses (default: coral)
- SERVER_HOST: Host to bind server (default: 0.0.0.0)
- SERVER_PORT: Port to bind server (default: 5000)
- DEFAULT_SAMPLE_RATE: Default audio sample rate (default: 24000)
- MAX_CHUNK_SIZE_MS: Maximum chunk size in milliseconds (default: 200)
- COMPANY_NAME: Your company name (default: Your AI Company)
- ASSISTANT_NAME: Assistant name (default: Sarah)

Author: Agent Stream Team
Version: 2.0.0
License: MIT
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
 """Production configuration class with environment variable support."""

 # ========================
 # CORE API CONFIGURATION
 # ========================

 # OpenAI Configuration - REQUIRED
 OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
 OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-realtime-preview-2024-12-17")
 OPENAI_VOICE = os.getenv("OPENAI_VOICE", "coral")
 TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

 # ========================
 # SERVER CONFIGURATION
 # ========================

 SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
 SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

 # ========================
 # AUDIO CONFIGURATION
 # ========================

 # Supported sample rates (Hz)
 SUPPORTED_SAMPLE_RATES = [8000, 16000, 24000]
 DEFAULT_SAMPLE_RATE = int(os.getenv("DEFAULT_SAMPLE_RATE", "24000"))

 # Chunk size configuration (milliseconds)
 MIN_CHUNK_SIZE_MS = int(os.getenv("MIN_CHUNK_SIZE_MS", "20"))
 MAX_CHUNK_SIZE_MS = int(os.getenv("MAX_CHUNK_SIZE_MS", "200")) # Optimized for quality
 BUFFER_SIZE_MS = int(os.getenv("BUFFER_SIZE_MS", "50"))

 # ========================
 # FEATURE FLAGS
 # ========================

 # Enhanced features
 ENHANCED_EVENTS_ENABLED = os.getenv("ENHANCED_EVENTS_ENABLED", "true").lower() == "true"
 DYNAMIC_CHUNK_SIZING = os.getenv("DYNAMIC_CHUNK_SIZING", "true").lower() == "true"
 AUDIO_ENHANCEMENT_ENABLED = os.getenv("AUDIO_ENHANCEMENT_ENABLED", "true").lower() == "true"

 # ========================
 # BUSINESS CONFIGURATION
 # ========================

 COMPANY_NAME = os.getenv("COMPANY_NAME", "Your AI Company")
 ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Sarah")

 # Bot personalities for different use cases
 SALES_INSTRUCTIONS = """You are {assistant_name}, an AI sales representative for {company_name}.

Your personality is warm, professional, and solution-focused. You excel at building rapport and understanding customer needs.

Key responsibilities:
1. Engage prospects naturally and build trust
2. Understand their specific needs and pain points
3. Present relevant solutions that match their requirements
4. Handle objections professionally and provide value
5. Guide toward next steps (demo, trial, or consultation)

Communication style:
- Be conversational and natural, not robotic
- Use appropriate pauses and inflections
- Show genuine interest in helping
- Ask thoughtful follow-up questions
- Keep responses concise but informative

Remember: You're here to help solve problems, not just make sales. Focus on providing value."""

 SUPPORT_INSTRUCTIONS = """You are {assistant_name}, an AI customer support specialist for {company_name}.

Your personality is helpful, patient, and solution-oriented. You excel at resolving issues and ensuring customer satisfaction.

Key responsibilities:
1. Listen actively to customer concerns
2. Diagnose problems accurately and efficiently
3. Provide clear, step-by-step solutions
4. Escalate complex issues when necessary
5. Follow up to ensure resolution

Communication style:
- Be empathetic and understanding
- Speak clearly and at an appropriate pace
- Break down complex solutions into simple steps
- Confirm understanding before moving on
- Maintain a positive, helpful tone

Remember: Every interaction is an opportunity to build customer loyalty."""

 QUALIFICATION_INSTRUCTIONS = """You are {assistant_name}, an AI lead qualification specialist for {company_name}.

Your personality is professional, efficient, and insightful. You excel at identifying qualified prospects and gathering key information.

Key responsibilities:
1. Assess prospect fit and buying intent
2. Gather key qualification criteria (budget, authority, need, timeline)
3. Identify decision-makers and stakeholders
4. Understand current solutions and pain points
5. Schedule appropriate next steps with sales team

Communication style:
- Be professional but friendly
- Ask strategic, open-ended questions
- Listen for buying signals and pain points
- Summarize key findings clearly
- Maintain momentum toward next steps

Remember: Quality over quantity - focus on identifying truly qualified prospects."""

 COLLECTION_INSTRUCTIONS = """You are {assistant_name}, an AI collections specialist for {company_name}.

Your personality is professional, firm but fair, and solution-oriented. You excel at resolving payment issues while maintaining customer relationships.

Key responsibilities:
1. Contact customers about overdue accounts professionally
2. Understand reasons for payment delays
3. Negotiate realistic payment arrangements
4. Document all interactions and agreements
5. Escalate when necessary while preserving relationships

Communication style:
- Be respectful and professional at all times
- Show understanding of customer situations
- Focus on finding mutually beneficial solutions
- Be clear about consequences while remaining helpful
- Document everything accurately

Remember: The goal is payment resolution while maintaining the customer relationship."""

 # ========================
 # LOGGING CONFIGURATION
 # ========================

 LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
 LOG_FILE = os.getenv("LOG_FILE", "logs/realtime_bot.log")

 # ========================
 # PRODUCTION SETTINGS
 # ========================

 # Security
 ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
 MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "100"))
 CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "300")) # 5 minutes

 # Performance
 WORKER_PROCESSES = int(os.getenv("WORKER_PROCESSES", "1"))
 MAX_MESSAGE_SIZE = int(os.getenv("MAX_MESSAGE_SIZE", "1048576")) # 1MB

 # Monitoring
 HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
 METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"

 @classmethod
 def get_adaptive_chunk_size(cls, sample_rate: int) -> int:
 """
 Get adaptive chunk size based on sample rate.

 Higher sample rates use larger chunks for better efficiency,
 while lower sample rates use smaller chunks for lower latency.

 Args:
 sample_rate: Audio sample rate in Hz

 Returns:
 Optimal chunk size in milliseconds
 """
 if sample_rate >= 24000:
 return cls.MAX_CHUNK_SIZE_MS # 200ms for high quality
 elif sample_rate >= 16000:
 return cls.BUFFER_SIZE_MS # 50ms for standard quality
 else:
 return cls.MIN_CHUNK_SIZE_MS # 20ms for low latency

 @classmethod
 def get_chunk_size_bytes(cls, sample_rate: int, chunk_size_ms: int) -> int:
 """
 Calculate chunk size in bytes.

 Args:
 sample_rate: Audio sample rate in Hz
 chunk_size_ms: Chunk duration in milliseconds

 Returns:
 Chunk size in bytes (16-bit PCM)
 """
 samples_per_chunk = (sample_rate * chunk_size_ms) // 1000
 return samples_per_chunk * 2 # 16-bit = 2 bytes per sample

 @classmethod
 def get_session_config(cls, sample_rate: int, voice: str, bot_type: str = "sales") -> Dict[str, Any]:
 """
 Get OpenAI session configuration optimized for the given parameters.

 Args:
 sample_rate: Audio sample rate in Hz
 voice: Voice identifier for responses
 bot_type: Type of bot (sales, support, qualification, collection)

 Returns:
 OpenAI session configuration dictionary
 """
 # Determine optimal audio formats
 if sample_rate >= 16000:
 input_format = "pcm16"
 output_format = "pcm16"
 else:
 input_format = "g711_ulaw"
 output_format = "g711_ulaw"

 # Get instructions based on bot type
 instructions_map = {
 "sales": cls.SALES_INSTRUCTIONS,
 "support": cls.SUPPORT_INSTRUCTIONS,
 "qualification": cls.QUALIFICATION_INSTRUCTIONS,
 "collection": cls.COLLECTION_INSTRUCTIONS
 }

 instructions = instructions_map.get(bot_type, cls.SALES_INSTRUCTIONS)
 instructions = instructions.format(
 assistant_name=cls.ASSISTANT_NAME,
 company_name=cls.COMPANY_NAME
 )

 return {
 "modalities": ["text", "audio"],
 "instructions": instructions,
 "voice": voice,
 "input_audio_format": input_format,
 "output_audio_format": output_format,
 "input_audio_transcription": {
 "model": "whisper-1"
 },
 "turn_detection": {
 "type": "server_vad",
 "threshold": 0.5,
 "prefix_padding_ms": 300,
 "silence_duration_ms": 500
 },
 "tools": [],
 "tool_choice": "auto",
 "temperature": cls.TEMPERATURE,
 "max_response_output_tokens": 4096
 }

 @classmethod
 def validate_config(cls) -> bool:
 """
 Validate configuration settings.

 Returns:
 True if configuration is valid

 Raises:
 ValueError: If critical configuration is missing or invalid
 """
 # Check required settings
 if not cls.OPENAI_API_KEY:
 raise ValueError("OPENAI_API_KEY is required")

 if cls.DEFAULT_SAMPLE_RATE not in cls.SUPPORTED_SAMPLE_RATES:
 raise ValueError(f"DEFAULT_SAMPLE_RATE must be one of {cls.SUPPORTED_SAMPLE_RATES}")

 if cls.SERVER_PORT < 1 or cls.SERVER_PORT > 65535:
 raise ValueError("SERVER_PORT must be between 1 and 65535")

 if cls.MAX_CHUNK_SIZE_MS < cls.MIN_CHUNK_SIZE_MS:
 raise ValueError("MAX_CHUNK_SIZE_MS must be >= MIN_CHUNK_SIZE_MS")

 return True

 @classmethod
 def get_environment_info(cls) -> Dict[str, Any]:
 """
 Get current environment configuration for debugging.

 Returns:
 Dictionary with current configuration (sensitive data masked)
 """
 return {
 "openai_model": cls.OPENAI_MODEL,
 "openai_voice": cls.OPENAI_VOICE,
 "server_host": cls.SERVER_HOST,
 "server_port": cls.SERVER_PORT,
 "default_sample_rate": cls.DEFAULT_SAMPLE_RATE,
 "supported_sample_rates": cls.SUPPORTED_SAMPLE_RATES,
 "chunk_size_range": f"{cls.MIN_CHUNK_SIZE_MS}-{cls.MAX_CHUNK_SIZE_MS}ms",
 "enhanced_events": cls.ENHANCED_EVENTS_ENABLED,
 "dynamic_chunks": cls.DYNAMIC_CHUNK_SIZING,
 "audio_enhancement": cls.AUDIO_ENHANCEMENT_ENABLED,
 "company_name": cls.COMPANY_NAME,
 "assistant_name": cls.ASSISTANT_NAME,
 "api_key_configured": bool(cls.OPENAI_API_KEY),
 "log_level": cls.LOG_LEVEL,
 "max_connections": cls.MAX_CONNECTIONS
 } 