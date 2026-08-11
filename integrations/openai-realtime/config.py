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
    # Telephony default is 8 kHz (Exotel AgentStream). Override via env / ?sample-rate=.
    SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', '8000'))
    DEFAULT_SAMPLE_RATE = int(os.getenv('DEFAULT_SAMPLE_RATE', '8000'))
    SUPPORTED_SAMPLE_RATES = [8000, 16000, 24000]
    AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', '10'))
    MIN_CHUNK_SIZE_MS = int(os.getenv('MIN_CHUNK_SIZE_MS', '20'))
    MAX_CHUNK_SIZE_MS = int(os.getenv('MAX_CHUNK_SIZE_MS', '200'))
    BUFFER_SIZE_MS = int(os.getenv('BUFFER_SIZE_MS', '160'))
    SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', '0.01'))
    NOISE_THRESHOLD = float(os.getenv('NOISE_THRESHOLD', '0.01'))
    AUDIO_ENHANCEMENT_ENABLED = os.getenv('AUDIO_ENHANCEMENT_ENABLED', 'false').lower() == 'true'
    # Debug only: 200ms tone on Exotel connected (causes an audible beep before greeting).
    SEND_TEST_TONE = os.getenv('SEND_TEST_TONE', 'false').lower() == 'true'
    
    # ===== EXOTEL SPECIFIC =====
    EXOTEL_MARK_CLEAR_ENHANCED = os.getenv('EXOTEL_MARK_CLEAR_ENHANCED', 'true').lower() == 'true'
    # Fixed inbound chunks are clearer for Realtime than dumping variable-size bursts.
    EXOTEL_VARIABLE_CHUNK_SUPPORT = os.getenv('EXOTEL_VARIABLE_CHUNK_SUPPORT', 'false').lower() == 'true'
    DYNAMIC_CHUNK_SIZING = os.getenv('DYNAMIC_CHUNK_SIZING', 'false').lower() == 'true'
    # Match nodejs-voice-bot-framework OpenAI bot: 200ms = 3200 B @ 8 kHz (Exotel min chunk).
    EXOTEL_OUTBOUND_FRAME_MS = int(os.getenv('EXOTEL_OUTBOUND_FRAME_MS', '200'))
    # Resample OpenAI PCM24 in blocks matching outbound frame duration (continuity).
    OPENAI_RESAMPLE_BLOCK_MS = int(os.getenv('OPENAI_RESAMPLE_BLOCK_MS', '200'))
    # Fixed size when sending Exotel mic PCM up to OpenAI (after upsample).
    INBOUND_CHUNK_MS = int(os.getenv('INBOUND_CHUNK_MS', '20'))
    # Node OpenAI bot skips mic→OpenAI while bot speaks (cuts echo / muddy S2S).
    HALF_DUPLEX = os.getenv('HALF_DUPLEX', 'true').lower() == 'true'
    # 0 = send as soon as a frame is ready (Node sendMedia); 0.9 ≈ realtime pacing.
    OUTBOUND_PACE_FACTOR = float(os.getenv('OUTBOUND_PACE_FACTOR', '0'))
    # Pre-cache TTS greeting and play on start before Realtime connects (~0ms feel).
    INSTANT_GREETING = os.getenv('INSTANT_GREETING', 'true').lower() == 'true'
    GREETING_TEXT = os.getenv(
        'GREETING_TEXT',
        f"Hi! This is {os.getenv('SALES_BOT_NAME', 'Sarah')} from "
        f"{os.getenv('COMPANY_NAME', 'TechSolutions Inc.')}. How can I help you today?",
    )
    # Faster turn-taking (mirrors nodejs openai-realtime-bot.js VAD).
    VAD_THRESHOLD = float(os.getenv('VAD_THRESHOLD', '0.6'))
    VAD_PREFIX_PADDING_MS = int(os.getenv('VAD_PREFIX_PADDING_MS', '200'))
    VAD_SILENCE_DURATION_MS = int(os.getenv('VAD_SILENCE_DURATION_MS', '400'))
    
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
    
    # OpenAI GA Realtime PCM wire rate (input requires explicit rate; output is 24 kHz).
    OPENAI_PCM_RATE = 24000

    @classmethod
    def get_wire_audio_format(cls, sample_rate: int) -> str:
        """Internal wire format used for OpenAI ↔ Exotel conversion helpers.

        Always PCM16 on the OpenAI wire. Requesting audio/pcmu while GA still
        emitted linear PCM caused 24 kHz bytes to be decoded as 8 kHz μ-law →
        very low / slow pitch on the phone.
        """
        return 'pcm16'

    @classmethod
    def get_enhanced_session_config(cls, sample_rate: int, voice: str) -> Dict[str, Any]:
        """GA Realtime session.update payload (no OpenAI-Beta header)."""
        # Always negotiate PCM @ 24 kHz with OpenAI; resample to Exotel rate locally.
        # GA requires rate on both input and output for audio/pcm.
        input_format = {"type": "audio/pcm", "rate": cls.OPENAI_PCM_RATE}
        output_format = {"type": "audio/pcm", "rate": cls.OPENAI_PCM_RATE}

        return {
            "type": "realtime",
            "model": cls.OPENAI_MODEL,
            "output_modalities": ["audio"],
            "instructions": (
                f"You are {cls.SALES_BOT_NAME}, a professional sales representative "
                f"for {cls.COMPANY_NAME}. Be warm, concise, and helpful on phone calls. "
                "Never repeat or parrot the caller's words back to them."
            ),
            "audio": {
                "input": {
                    "format": input_format,
                    "turn_detection": {
                        "type": "server_vad",
                        # Faster turn-taking — matches nodejs-voice-bot-framework OpenAI bot.
                        "threshold": cls.VAD_THRESHOLD,
                        "prefix_padding_ms": cls.VAD_PREFIX_PADDING_MS,
                        "silence_duration_ms": cls.VAD_SILENCE_DURATION_MS,
                        "create_response": True,
                    },
                },
                "output": {
                    "format": output_format,
                    "voice": voice,
                },
            },
        } 