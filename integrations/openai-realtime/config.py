#!/usr/bin/env python3
"""
Configuration settings for the Voice AI Bot System
This file contains all configurable parameters for the application.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Main configuration class for the Voice AI Bot System"""
    
    # ===== CORE API SETTINGS =====
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-realtime-preview-2024-12-17')
    OPENAI_VOICE = os.getenv('OPENAI_VOICE', 'coral')
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
    # ===== SERVER SETTINGS =====
    SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))
    WEB_DASHBOARD_PORT = int(os.getenv('WEB_DASHBOARD_PORT', '5001'))
    
    # ===== LOGGING =====
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ===== AUDIO PROCESSING =====
    SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', '24000'))
    DEFAULT_SAMPLE_RATE = int(os.getenv('DEFAULT_SAMPLE_RATE', '24000'))
    SUPPORTED_SAMPLE_RATES = [8000, 16000, 24000]
    AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', '10'))
    MIN_CHUNK_SIZE_MS = int(os.getenv('MIN_CHUNK_SIZE_MS', '20'))
    MAX_CHUNK_SIZE_MS = int(os.getenv('MAX_CHUNK_SIZE_MS', '200'))
    BUFFER_SIZE_MS = int(os.getenv('BUFFER_SIZE_MS', '160'))
    SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', '0.01'))
    NOISE_THRESHOLD = float(os.getenv('NOISE_THRESHOLD', '0.01'))
    AUDIO_ENHANCEMENT_ENABLED = os.getenv('AUDIO_ENHANCEMENT_ENABLED', 'false').lower() == 'true'
    
    # ===== EXOTEL SPECIFIC =====
    EXOTEL_MARK_CLEAR_ENHANCED = os.getenv('EXOTEL_MARK_CLEAR_ENHANCED', 'true').lower() == 'true'
    EXOTEL_VARIABLE_CHUNK_SUPPORT = os.getenv('EXOTEL_VARIABLE_CHUNK_SUPPORT', 'true').lower() == 'true'
    DYNAMIC_CHUNK_SIZING = os.getenv('DYNAMIC_CHUNK_SIZING', 'true').lower() == 'true'
    
    # ===== BOT PERSONALITY =====
    SALES_BOT_NAME = os.getenv('SALES_BOT_NAME', 'Sarah')
    SALES_REP_NAME = os.getenv('SALES_REP_NAME', 'Sarah')  # Alias for compatibility
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'TechSolutions Inc.')
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))
    
    # ===== AI ENGINE PREFERENCES =====
    PRIMARY_STT_PROVIDER = os.getenv('PRIMARY_STT_PROVIDER', 'whisper')
    PRIMARY_TTS_PROVIDER = os.getenv('PRIMARY_TTS_PROVIDER', 'gtts')
    PREFER_LLM_NLP = os.getenv('PREFER_LLM_NLP', 'true').lower() == 'true'
    RESAMPLER_BACKEND = os.getenv('RESAMPLER_BACKEND', 'pydub')
    
    # ===== PERFORMANCE =====
    MAX_CONCURRENT_CALLS = int(os.getenv('MAX_CONCURRENT_CALLS', '50'))
    CALL_TIMEOUT_SECONDS = int(os.getenv('CALL_TIMEOUT_SECONDS', '1800'))
    
    # ===== SECURITY =====
    REQUIRE_AUTH = os.getenv('REQUIRE_AUTH', 'false').lower() == 'true'
    RATE_LIMITING_ENABLED = os.getenv('RATE_LIMITING_ENABLED', 'true').lower() == 'true'
    
    # ===== MONITORING =====
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    DETAILED_ANALYTICS = os.getenv('DETAILED_ANALYTICS', 'true').lower() == 'true'
    CONVERSATION_RECORDING = os.getenv('CONVERSATION_RECORDING', 'true').lower() == 'true'
    
    # ===== PRODUCTION MODE =====
    PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
    
    # ===== PRODUCTS/SERVICES CONFIGURATION =====
    PRODUCTS = [
        {
            "name": "AI Voice Assistant Pro",
            "price": "$99/month",
            "description": "Advanced AI-powered voice assistant for customer support"
        },
        {
            "name": "Custom Bot Development",
            "price": "$299/month", 
            "description": "Tailored voice bot solutions for your specific business needs"
        },
        {
            "name": "Enterprise Voice Platform",
            "price": "$599/month",
            "description": "Full-scale voice AI platform with analytics and integrations"
        }
    ]
    
    # ===== VALIDATION =====
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
            
        if not cls.COMPANY_NAME:
            errors.append("COMPANY_NAME is required")
            
        if cls.SERVER_PORT < 1 or cls.SERVER_PORT > 65535:
            errors.append("SERVER_PORT must be between 1 and 65535")
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    # ===== HELPER METHODS =====
    @classmethod
    def get_openai_config(cls) -> Dict[str, Any]:
        """Get OpenAI-specific configuration"""
        return {
            'api_key': cls.OPENAI_API_KEY,
            'model': cls.OPENAI_MODEL,
            'voice': cls.OPENAI_VOICE,
            'temperature': cls.OPENAI_TEMPERATURE
        }
    
    @classmethod
    def get_server_config(cls) -> Dict[str, Any]:
        """Get server configuration"""
        return {
            'host': cls.SERVER_HOST,
            'port': cls.SERVER_PORT,
            'dashboard_port': cls.WEB_DASHBOARD_PORT
        }
    
    @classmethod
    def get_audio_config(cls) -> Dict[str, Any]:
        """Get audio processing configuration"""
        return {
            'sample_rate': cls.SAMPLE_RATE,
            'chunk_size': cls.AUDIO_CHUNK_SIZE,
            'min_chunk_size_ms': cls.MIN_CHUNK_SIZE_MS,
            'buffer_size_ms': cls.BUFFER_SIZE_MS,
            'silence_threshold': cls.SILENCE_THRESHOLD
        }
    
    @classmethod
    def get_adaptive_chunk_size(cls, sample_rate: int) -> int:
        """Get adaptive chunk size based on sample rate"""
        if sample_rate >= 24000:
            return 40  # 40ms for 24kHz
        elif sample_rate >= 16000:
            return 30  # 30ms for 16kHz
        else:
            return 20  # 20ms for 8kHz
    
    @classmethod
    def get_chunk_size_bytes(cls, sample_rate: int, chunk_size_ms: int) -> int:
        """Calculate chunk size in bytes"""
        return int(sample_rate * chunk_size_ms / 1000) * 2  # 2 bytes per sample (16-bit)
    
    @classmethod
    def get_enhanced_session_config(cls, sample_rate: int, voice: str) -> Dict[str, Any]:
        """Get enhanced session configuration"""
        return {
            'model': cls.OPENAI_MODEL,
            'voice': voice,
            'input_audio_format': 'g711_ulaw',
            'output_audio_format': 'g711_ulaw',
            'input_audio_transcription': {'model': 'whisper-1'},
            'turn_detection': {'type': 'server_vad', 'threshold': 0.5},
            'temperature': cls.TEMPERATURE,
            'max_response_output_tokens': 4096
        } 