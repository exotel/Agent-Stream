import os
from dotenv import load_dotenv
from typing import Dict, Any
from app.configs.prompts import (
    GEMINI_SALES_AGENT_SYSTEM_INSTRUCTION,
    GEMINI_SALES_AGENT_GREETING_PROMPT,
    get_gemini_sales_agent_system_instruction,
    get_gemini_sales_agent_greeting_prompt
)

load_dotenv()

class Config:
    # gemini configs 
    GEMINI_LIVE_WS_URL = os.getenv("GOOGLE_LIVE_WS")
    GEMINI_LIVE_WS_API_KEY = os.getenv("GOOGLE_LIVE_WS_API")
    # exotel configs
    EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
    EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
    EXOTEL_SUBDOMAIN = os.getenv("EXOTEL_SUBDOMAIN")
    EXOTEL_SID = os.getenv("EXOTEL_SID")
    EXOTEL_SALES_AGENT_APP_ID = os.getenv("EXOTEL_SALES_AGENT_APP_ID")
    # Caller ID shown to the callee when making outbound calls
    EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID")

    # audio processing 
    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", '16000'))
    DEFAULT_SAMPLE_RATE = int(os.getenv("DEFAULT_SAMPLE_RATE", '16000'))
    SUPPORTED_SAMPLE_RATES = [8000,16000,24000]

    AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', '3200'))
    MIN_CHUNK_SIZE_MS = int(os.getenv('MIN_CHUNK_SIZE_MS', '100'))
    MAX_CHUNK_SIZE_MS = int(os.getenv('MAX_CHUNK_SIZE_MS', '3200'))
    BUFFER_SIZE_MS = int(os.getenv('BUFFER_SIZE_MS', '200'))
    SILENCE_THRESHOLD = float(os.getenv('SILENCE_THRESHOLD', '0.01'))
    NOISE_THRESHOLD = float(os.getenv('NOISE_THRESHOLD', '0.01'))
    AUDIO_ENHANCEMENT_ENABLED = os.getenv('AUDIO_ENHANCEMENT_ENABLED', 'false').lower() == 'true'

    # exotel audio metadata
    EXOTEL_MARK_CLEAR_ENHANCED = os.getenv('EXOTEL_MARK_CLEAR_ENHANCED', 'true').lower() == 'true'
    EXOTEL_VARIABLE_CHUNK_SUPPORT = os.getenv('EXOTEL_VARIABLE_CHUNK_SUPPORT', 'true').lower() == 'true'
    DYNAMIC_CHUNK_SIZING = os.getenv('DYNAMIC_CHUNK_SIZING', 'false').lower() == 'true'
    # Exotel: send silent PCM during gaps to improve RX count and prevent timeouts (recommended by Exotel)
    EXOTEL_SILENCE_DURING_GAPS = os.getenv('EXOTEL_SILENCE_DURING_GAPS', 'true').lower() == 'true'
    EXOTEL_SILENCE_GAP_MS = int(os.getenv('EXOTEL_SILENCE_GAP_MS', '200'))

    # ai agent preferences
    PRIMARY_STT_PROVIDER = os.getenv('PRIMARY_STT_PROVIDER', 'whisper')
    PRIMARY_TTS_PROVIDER = os.getenv('PRIMARY_TTS_PROVIDER', 'gtts')
    PREFER_LLM_NLP = os.getenv('PREFER_LLM_NLP', 'true').lower() == 'true'
    RESAMPLER_BACKEND = os.getenv('RESAMPLER_BACKEND', 'pydub')

    # sales agent prompts (defaults without personalization)
    SALES_AGENT_SYSTEM_INSTRUCTION = GEMINI_SALES_AGENT_SYSTEM_INSTRUCTION
    SALES_AGENT_GREETING_PROMPT = GEMINI_SALES_AGENT_GREETING_PROMPT

    @classmethod
    def get_personalized_system_instruction(cls, customer_name: str = None) -> str:
        """Get system instruction personalized with customer name."""
        return get_gemini_sales_agent_system_instruction(customer_name)
    
    @classmethod
    def get_personalized_greeting_prompt(cls, customer_name: str = None) -> str:
        """Get greeting prompt personalized with customer name."""
        return get_gemini_sales_agent_greeting_prompt(customer_name)

    MAX_CONCURRENT_CALLS = int(os.getenv('MAX_CONCURRENT_CALLS', '50'))
    CALL_TIMEOUT_SECONDS = int(os.getenv('CALL_TIMEOUT_SECONDS', '1800'))
    # Health check interval (seconds). First check runs after this delay; avoid 60s if Gemini/bot stops at 1 min.
    EXOTEL_HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv('EXOTEL_HEALTH_CHECK_INTERVAL_SECONDS', '120'))
    
    REQUIRE_AUTH = os.getenv('REQUIRE_AUTH', 'false').lower() == 'true'
    RATE_LIMITING_ENABLED = os.getenv('RATE_LIMITING_ENABLED', 'true').lower() == 'true'

    PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'

    @classmethod
    def validate(cls):
        errors = []
        if not cls.GEMINI_LIVE_WS_URL:
            errors.append("GEMINI_LIVE_WS_URL is required")
        if not cls.GEMINI_LIVE_WS_API_KEY:
            errors.append("GEMINI_LIVE_WS_API_KEY is required")
        # When running locally for WSS-only (e.g. ngrok), skip Exotel/Redis validation
        if os.getenv("SKIP_FULL_VALIDATION", "").lower() in ("1", "true", "yes"):
            if errors:
                raise ValueError("Config validation errors:\n" + "\n".join(errors))
            return errors
        if not cls.EXOTEL_API_TOKEN:
            errors.append("EXOTEL_API_TOKEN is required")
        if not cls.EXOTEL_API_KEY:
            errors.append("EXOTEL_API_KEY is required")
        if not cls.EXOTEL_SUBDOMAIN:
            errors.append("EXOTEL_SUBDOMAIN is required")
        if not cls.EXOTEL_SID:
            errors.append("EXOTEL_SID is required")
        if not cls.EXOTEL_SALES_AGENT_APP_ID:
            errors.append("EXOTEL_SALES_AGENT_APP_ID is required")
        if not cls.EXOTEL_CALLER_ID:
            errors.append("EXOTEL_CALLER_ID is required for outbound calls")
        if errors:
            raise ValueError("Config validation errors:\n" + "\n".join(errors))
        return errors

    @classmethod
    def get_audio_configs(cls) -> Dict[str, Any]:
        return {
            'sample_rate': cls.SAMPLE_RATE,
            'chunk_size': cls.AUDIO_CHUNK_SIZE,
            'min_chunk_size_ms': cls.MIN_CHUNK_SIZE_MS,
            'buffer_size_ms': cls.BUFFER_SIZE_MS,
            'silence_threshold': cls.SILENCE_THRESHOLD
        }
    
    # Audio chunk size constants (PCM 16-bit mono)
    BYTES_PER_SAMPLE = 2
    MIN_CHUNK_BYTES = 3200      # 3.2 KB minimum
    MAX_CHUNK_BYTES = 102400    # 100 KB maximum
    CHUNK_ALIGNMENT = 320       # Must be multiple of 320 bytes

    @classmethod
    def _normalize_chunk_bytes(cls, chunk_bytes: int) -> int:
        chunk_bytes = max(cls.MIN_CHUNK_BYTES, min(cls.MAX_CHUNK_BYTES, chunk_bytes))
        if chunk_bytes % cls.CHUNK_ALIGNMENT != 0:
            chunk_bytes = ((chunk_bytes // cls.CHUNK_ALIGNMENT) + 1) * cls.CHUNK_ALIGNMENT
        return chunk_bytes

    @classmethod
    def _ms_to_bytes(cls, sample_rate: int, ms: int) -> int:
        return int(sample_rate * ms / 1000) * cls.BYTES_PER_SAMPLE

    @classmethod
    def _bytes_to_ms(cls, sample_rate: int, num_bytes: int) -> int:
        return int(num_bytes / cls.BYTES_PER_SAMPLE / sample_rate * 1000)

    @classmethod
    def get_adaptive_chunk_size(cls, sample_rate: int) -> int:
        """
        Get adaptive chunk size (in ms) based on sample rate.
        Returns chunk size that respects byte constraints (min 3.2KB, max 100KB, aligned to 320 bytes).
        """
        # Select initial chunk size based on sample rate
        if sample_rate >= 24000:
            chunk_ms = 40
        elif sample_rate >= 16000:
            chunk_ms = 30
        else:
            chunk_ms = 20

        chunk_bytes = cls._normalize_chunk_bytes(cls._ms_to_bytes(sample_rate, chunk_ms))
        return max(cls._bytes_to_ms(sample_rate, chunk_bytes), 1)

    @classmethod
    def get_chunk_size_bytes(cls, sample_rate: int, chunk_size_ms: int) -> int:
        """
        Calculate chunk size in bytes for given sample rate and duration.
        Returns size clamped to valid range and aligned to 320 bytes.
        """
        return cls._normalize_chunk_bytes(cls._ms_to_bytes(sample_rate, chunk_size_ms))
    
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