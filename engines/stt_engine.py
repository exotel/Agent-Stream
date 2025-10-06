"""
Production-ready Speech-to-Text Engine
Supports multiple STT providers with automatic fallback
"""

import logging
import asyncio
import io
import tempfile
import os
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import config

logger = logging.getLogger(__name__)

class STTProvider(ABC):
    """Abstract base class for STT providers"""
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes, sample_rate: int = 8000, language: str = "en-US") -> Optional[str]:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass

class OpenAIWhisperSTT(STTProvider):
    """OpenAI Whisper STT Provider"""
    
    def __init__(self):
        self.client = None
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("OpenAI Whisper STT initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI Whisper: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None and config.OPENAI_API_KEY != "your-openai-api-key-here"
    
    async def transcribe(self, audio_data: bytes, sample_rate: int = 8000, language: str = "en-US") -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            # Convert audio data to a format suitable for Whisper
            from pydub import AudioSegment
            
            # Create audio segment from raw data
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=2,  # 16-bit
                frame_rate=sample_rate,
                channels=1
            )
            
            # Export to WAV format for Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                audio_segment.export(temp_file.name, format="wav")
                temp_file_path = temp_file.name
            
            try:
                # Transcribe with Whisper
                with open(temp_file_path, "rb") as audio_file:
                    transcript = await asyncio.to_thread(
                        self.client.audio.transcriptions.create,
                        model="whisper-1",
                        file=audio_file,
                        language=language[:2]  # Whisper expects 'en' not 'en-US'
                    )
                
                result = transcript.text.strip()
                logger.info(f"Whisper transcription: {result}")
                return result
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"OpenAI Whisper transcription error: {e}")
            return None

class VoskSTT(STTProvider):
    """Vosk STT Provider (offline fallback)"""
    
    def __init__(self):
        self.model = None
        self.rec = None
        try:
            import vosk
            import json
            
            # Try to load Vosk model
            model_path = getattr(config, 'VOSK_MODEL_PATH', 'vosk-model-en-us-0.22')
            if os.path.exists(model_path):
                vosk.SetLogLevel(-1)  # Disable Vosk logging
                self.model = vosk.Model(model_path)
                logger.info("Vosk STT initialized")
            else:
                logger.warning(f"Vosk model not found at {model_path}")
                
        except ImportError:
            logger.warning("Vosk not installed - STT fallback unavailable")
        except Exception as e:
            logger.error(f"Failed to initialize Vosk: {e}")
    
    def is_available(self) -> bool:
        return self.model is not None
    
    async def transcribe(self, audio_data: bytes, sample_rate: int = 8000, language: str = "en-US") -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            import vosk
            import json
            
            # Create recognizer for this audio
            rec = vosk.KaldiRecognizer(self.model, sample_rate)
            
            # Process audio data
            if rec.AcceptWaveform(audio_data):
                result = json.loads(rec.Result())
                text = result.get('text', '').strip()
                logger.info(f"Vosk transcription: {text}")
                return text
            else:
                # Partial result
                result = json.loads(rec.PartialResult())
                text = result.get('partial', '').strip()
                if text:
                    logger.info(f"Vosk partial transcription: {text}")
                    return text
                    
        except Exception as e:
            logger.error(f"Vosk transcription error: {e}")
            return None

class GoogleSTT(STTProvider):
    """Google Speech-to-Text Provider"""
    
    def __init__(self):
        self.client = None
        try:
            from google.cloud import speech
            self.client = speech.SpeechClient()
            logger.info("Google STT initialized")
        except Exception as e:
            logger.warning(f"Google STT not available: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None and os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    async def transcribe(self, audio_data: bytes, sample_rate: int = 8000, language: str = "en-US") -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            from google.cloud import speech
            
            audio = speech.RecognitionAudio(content=audio_data)
            config_google = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language,
            )
            
            response = await asyncio.to_thread(
                self.client.recognize,
                config=config_google,
                audio=audio
            )
            
            if response.results:
                text = response.results[0].alternatives[0].transcript.strip()
                logger.info(f"Google STT transcription: {text}")
                return text
                
        except Exception as e:
            logger.error(f"Google STT transcription error: {e}")
            return None

class ProductionSTTEngine:
    """Production STT Engine with multiple providers and fallback"""
    
    def __init__(self):
        self.providers = []
        
        # Initialize providers in order of preference
        primary_provider = getattr(config, 'PRIMARY_STT_PROVIDER', 'whisper')
        
        if primary_provider == 'whisper':
            self.providers = [
                OpenAIWhisperSTT(),
                GoogleSTT(),
                VoskSTT()
            ]
        elif primary_provider == 'google':
            self.providers = [
                GoogleSTT(),
                OpenAIWhisperSTT(),
                VoskSTT()
            ]
        else:
            self.providers = [
                VoskSTT(),
                OpenAIWhisperSTT(),
                GoogleSTT()
            ]
        
        # Filter to only available providers
        self.available_providers = [p for p in self.providers if p.is_available()]
        
        logger.info(f"STT Engine initialized with {len(self.available_providers)} providers")
        for i, provider in enumerate(self.available_providers):
            logger.info(f"  {i+1}. {provider.__class__.__name__}")
    
    async def transcribe(self, audio_data: bytes, sample_rate: int = 8000, language: str = "en-US") -> Optional[str]:
        """Transcribe audio using available providers with fallback"""
        
        if not self.available_providers:
            logger.error("No STT providers available")
            return None
        
        for i, provider in enumerate(self.available_providers):
            try:
                result = await provider.transcribe(audio_data, sample_rate, language)
                if result and len(result.strip()) > 0:
                    if i > 0:  # Used fallback
                        logger.info(f"STT fallback successful with {provider.__class__.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"STT provider {provider.__class__.__name__} failed: {e}")
                continue
        
        logger.error("All STT providers failed")
        return None
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        for provider in self.providers:
            status[provider.__class__.__name__] = {
                'available': provider.is_available(),
                'type': 'primary' if provider in self.available_providers[:1] else 'fallback'
            }
        return status 