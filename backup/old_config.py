#!/usr/bin/env python3
"""
Enhanced Configuration for Agent Stream Bot Framework
Centralized configuration management with environment variable support
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Enhanced configuration class with environment variable support"""
    
    # ========================
    # CORE API CONFIGURATION
    # ========================
    
    # OpenAI Configuration - SECURE: Load from environment
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
    
    # Enhanced multi-sample rate support
    SUPPORTED_SAMPLE_RATES = [8000, 16000, 24000]
    DEFAULT_SAMPLE_RATE = int(os.getenv("DEFAULT_SAMPLE_RATE", "16000"))
    
    # Enhanced chunk size configuration
    MIN_CHUNK_SIZE_MS = int(os.getenv("MIN_CHUNK_SIZE_MS", "20"))
    MAX_CHUNK_SIZE_MS = int(os.getenv("MAX_CHUNK_SIZE_MS", "200"))  # Increased to 200ms for better quality
    BUFFER_SIZE_MS = int(os.getenv("BUFFER_SIZE_MS", "50"))
    
    # Enhanced audio processing
    AUDIO_ENHANCEMENT_ENABLED = os.getenv("AUDIO_ENHANCEMENT_ENABLED", "true").lower() == "true"
    NOISE_THRESHOLD = float(os.getenv("NOISE_THRESHOLD", "100"))
    
    # ========================
    # ENHANCED EXOTEL FEATURES
    # ========================
    
    # Enhanced mark/clear event support
    EXOTEL_MARK_CLEAR_ENHANCED = os.getenv("EXOTEL_MARK_CLEAR_ENHANCED", "true").lower() == "true"
    EXOTEL_VARIABLE_CHUNK_SUPPORT = os.getenv("EXOTEL_VARIABLE_CHUNK_SUPPORT", "true").lower() == "true"
    DYNAMIC_CHUNK_SIZING = os.getenv("DYNAMIC_CHUNK_SIZING", "true").lower() == "true"
    
    # ========================
    # BOT PERSONALITY & COMPANY
    # ========================
    
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company")
    SALES_REP_NAME = os.getenv("SALES_REP_NAME", "Sarah")
    PRODUCTS = os.getenv("PRODUCTS", "Our premium solutions").split(",")
    
    # ========================
    # LOGGING CONFIGURATION
    # ========================
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # ========================
    # NGROK CONFIGURATION
    # ========================
    
    NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not cls.OPENAI_API_KEY.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        
        if cls.DEFAULT_SAMPLE_RATE not in cls.SUPPORTED_SAMPLE_RATES:
            raise ValueError(f"DEFAULT_SAMPLE_RATE must be one of: {cls.SUPPORTED_SAMPLE_RATES}")
    
    @classmethod
    def get_chunk_size_bytes(cls, sample_rate: int, chunk_ms: int) -> int:
        """Calculate chunk size in bytes for given sample rate and duration"""
        # PCM 16-bit = 2 bytes per sample
        return int((sample_rate * chunk_ms / 1000) * 2)
    
    @classmethod
    def get_adaptive_chunk_size(cls, sample_rate: int) -> int:
        """Get adaptive chunk size based on sample rate"""
        if sample_rate >= 24000:
            return cls.MAX_CHUNK_SIZE_MS  # Larger chunks for high sample rates
        elif sample_rate >= 16000:
            return cls.BUFFER_SIZE_MS     # Medium chunks for standard rates
        else:
            return cls.MIN_CHUNK_SIZE_MS  # Smaller chunks for low sample rates
    
    @classmethod
    def get_enhanced_session_config(cls, sample_rate: int, voice: str) -> Dict[str, Any]:
        """Get enhanced OpenAI session configuration based on sample rate"""
        
        # Determine optimal audio formats based on sample rate
        if sample_rate >= 16000:
            input_format = "pcm16"
            output_format = "pcm16"
        else:
            input_format = "g711_ulaw"
            output_format = "g711_ulaw"
        
        return {
            "modalities": ["text", "audio"],
            "instructions": f"""You are {cls.SALES_REP_NAME}, an AI sales representative for {cls.COMPANY_NAME}. 
            
Your personality is warm, professional, and solution-focused. You have deep knowledge about our products: {', '.join(cls.PRODUCTS)}.

Key responsibilities:
1. Engage prospects naturally and build rapport
2. Understand their specific needs and challenges  
3. Present relevant solutions that match their requirements
4. Handle objections professionally and provide value
5. Guide toward next steps (demo, trial, or consultation)

Communication style:
- Be conversational and natural, not robotic
- Use appropriate pauses and inflections  
- Show genuine interest in helping
- Ask thoughtful follow-up questions
- Keep responses concise but informative

Audio quality: This call is running at {sample_rate}Hz. Adjust your speech pace and clarity accordingly.

Remember: You're here to help solve problems, not just make sales. Focus on providing value.""",
            
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
            "tools": [
                {
                    "type": "function",
                    "name": "schedule_demo",
                    "description": "Schedule a product demonstration for interested prospects",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string", "description": "Customer's full name"},
                            "company": {"type": "string", "description": "Customer's company name"},
                            "contact_email": {"type": "string", "description": "Customer's email address"},
                            "contact_phone": {"type": "string", "description": "Customer's phone number"},
                            "product_interest": {"type": "string", "description": "Specific product or solution they're interested in"},
                            "preferred_date": {"type": "string", "description": "Preferred demo date"},
                            "preferred_time": {"type": "string", "description": "Preferred demo time"},
                            "additional_notes": {"type": "string", "description": "Any additional requirements or notes"}
                        },
                        "required": ["customer_name", "contact_email", "product_interest"]
                    }
                },
                {
                    "type": "function", 
                    "name": "send_pricing_info",
                    "description": "Send detailed pricing information to qualified prospects",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product": {"type": "string", "description": "Product or service for pricing"},
                            "company_size": {"type": "string", "description": "Size of customer's company (startup, small, medium, enterprise)"},
                            "contact_email": {"type": "string", "description": "Email to send pricing information"},
                            "custom_requirements": {"type": "string", "description": "Any custom requirements that may affect pricing"}
                        },
                        "required": ["product", "contact_email"]
                    }
                },
                {
                    "type": "function",
                    "name": "transfer_to_human",
                    "description": "Transfer the customer to a human sales representative",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for transfer (complex_request, pricing_negotiation, technical_question, customer_request, etc.)"},
                            "customer_context": {"type": "string", "description": "Summary of conversation and customer needs"},
                            "urgency": {"type": "string", "description": "Priority level (low, medium, high, urgent)"}
                        },
                        "required": ["reason", "customer_context"]
                    }
                }
            ],
            "tool_choice": "auto",
            "temperature": cls.TEMPERATURE,
            "max_response_output_tokens": 2000
        } 