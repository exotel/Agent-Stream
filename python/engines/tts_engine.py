"""
Production-ready Text-to-Speech Engine
Supports multiple TTS providers with automatic fallback
"""

import logging
import asyncio
import tempfile
import os
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod
import config

logger = logging.getLogger(__name__)

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_voices(self) -> list:
        pass

class GoogleTTS(TTSProvider):
    """Google Text-to-Speech Provider"""
    
    def __init__(self):
        self.client = None
        try:
            from google.cloud import texttospeech
            self.client = texttospeech.TextToSpeechClient()
            logger.info("Google TTS initialized")
        except Exception as e:
            logger.warning(f"Google TTS not available: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None and os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    def get_voices(self) -> list:
        if not self.is_available():
            return []
        
        try:
            from google.cloud import texttospeech
            voices = self.client.list_voices()
            return [voice.name for voice in voices.voices if voice.language_codes[0].startswith('en')]
        except:
            return ['en-US-Standard-A', 'en-US-Standard-B']
    
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        if not self.is_available():
            return None
        
        try:
            from google.cloud import texttospeech
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Voice selection
            if not voice:
                voice = 'en-US-Standard-A' if language.startswith('en') else f'{language}-Standard-A'
            
            voice_config = texttospeech.VoiceSelectionParams(
                language_code=language if '-' in language else f'{language}-US',
                name=voice
            )
            
            # Audio config for 8kHz output (Exotel compatible)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=8000
            )
            
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            logger.info(f"Google TTS synthesis successful: {len(response.audio_content)} bytes")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Google TTS synthesis error: {e}")
            return None

class gTTSProvider(TTSProvider):
    """Google Text-to-Speech (gTTS) Provider - Free tier"""
    
    def __init__(self):
        self.available = False
        try:
            from gtts import gTTS
            self.available = True
            logger.info("gTTS initialized")
        except ImportError:
            logger.warning("gTTS not available")
    
    def is_available(self) -> bool:
        return self.available
    
    def get_voices(self) -> list:
        return ['default'] if self.available else []
    
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        if not self.is_available():
            return None
        
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            
            # Create TTS object
            tts = gTTS(text=text, lang=language[:2], slow=False)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                await asyncio.to_thread(tts.save, temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Convert MP3 to WAV with appropriate sample rate
                audio_segment = AudioSegment.from_mp3(temp_file_path)
                audio_segment = audio_segment.set_frame_rate(8000).set_channels(1)
                
                # Export to bytes
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                    audio_segment.export(wav_file.name, format="wav")
                    wav_file_path = wav_file.name
                
                try:
                    with open(wav_file_path, "rb") as f:
                        audio_data = f.read()
                    
                    logger.info(f"gTTS synthesis successful: {len(audio_data)} bytes")
                    return audio_data
                    
                finally:
                    if os.path.exists(wav_file_path):
                        os.unlink(wav_file_path)
                        
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"gTTS synthesis error: {e}")
            return None

class CoquiTTS(TTSProvider):
    """Coqui TTS Provider - Open source alternative"""
    
    def __init__(self):
        self.model = None
        try:
            from TTS.api import TTS
            # Use a lightweight model for faster inference
            model_name = getattr(config, 'COQUI_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')
            self.model = TTS(model_name)
            logger.info("Coqui TTS initialized")
        except Exception as e:
            logger.warning(f"Coqui TTS not available: {e}")
    
    def is_available(self) -> bool:
        return self.model is not None
    
    def get_voices(self) -> list:
        return ['default'] if self.is_available() else []
    
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        if not self.is_available():
            return None
        
        try:
            from pydub import AudioSegment
            
            # Generate audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # Synthesize speech
                await asyncio.to_thread(
                    self.model.tts_to_file,
                    text=text,
                    file_path=temp_file_path
                )
                
                # Convert to appropriate format
                audio_segment = AudioSegment.from_wav(temp_file_path)
                audio_segment = audio_segment.set_frame_rate(8000).set_channels(1)
                
                # Export to bytes
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                    audio_segment.export(wav_file.name, format="wav")
                    wav_file_path = wav_file.name
                
                try:
                    with open(wav_file_path, "rb") as f:
                        audio_data = f.read()
                    
                    logger.info(f"Coqui TTS synthesis successful: {len(audio_data)} bytes")
                    return audio_data
                    
                finally:
                    if os.path.exists(wav_file_path):
                        os.unlink(wav_file_path)
                        
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Coqui TTS synthesis error: {e}")
            return None

class PyttsxTTS(TTSProvider):
    """Pyttsx3 TTS Provider - System fallback"""
    
    def __init__(self):
        self.engine = None
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # Set properties for better quality
            self.engine.setProperty('rate', 150)  # Speed
            self.engine.setProperty('volume', 0.9)  # Volume
            logger.info("Pyttsx3 TTS initialized")
        except Exception as e:
            logger.warning(f"Pyttsx3 TTS not available: {e}")
    
    def is_available(self) -> bool:
        return self.engine is not None
    
    def get_voices(self) -> list:
        if not self.is_available():
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [voice.id for voice in voices if voice]
        except:
            return ['default']
    
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        if not self.is_available():
            return None
        
        try:
            from pydub import AudioSegment
            
            # Set voice if specified
            if voice and voice != 'default':
                voices = self.engine.getProperty('voices')
                for v in voices:
                    if voice in v.id:
                        self.engine.setProperty('voice', v.id)
                        break
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # Synthesize to file
                await asyncio.to_thread(
                    lambda: (
                        self.engine.save_to_file(text, temp_file_path),
                        self.engine.runAndWait()
                    )
                )
                
                # Convert to appropriate format
                audio_segment = AudioSegment.from_wav(temp_file_path)
                audio_segment = audio_segment.set_frame_rate(8000).set_channels(1)
                
                # Export to bytes
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                    audio_segment.export(wav_file.name, format="wav")
                    wav_file_path = wav_file.name
                
                try:
                    with open(wav_file_path, "rb") as f:
                        audio_data = f.read()
                    
                    logger.info(f"Pyttsx3 TTS synthesis successful: {len(audio_data)} bytes")
                    return audio_data
                    
                finally:
                    if os.path.exists(wav_file_path):
                        os.unlink(wav_file_path)
                        
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Pyttsx3 TTS synthesis error: {e}")
            return None

class ProductionTTSEngine:
    """Production TTS Engine with multiple providers and fallback"""
    
    def __init__(self):
        self.providers = []
        
        # Initialize providers in order of preference
        primary_provider = getattr(config, 'PRIMARY_TTS_PROVIDER', 'google')
        
        if primary_provider == 'google':
            self.providers = [
                GoogleTTS(),
                gTTSProvider(),
                CoquiTTS(),
                PyttsxTTS()
            ]
        elif primary_provider == 'coqui':
            self.providers = [
                CoquiTTS(),
                GoogleTTS(),
                gTTSProvider(),
                PyttsxTTS()
            ]
        else:  # gtts
            self.providers = [
                gTTSProvider(),
                GoogleTTS(),
                CoquiTTS(),
                PyttsxTTS()
            ]
        
        # Filter to only available providers
        self.available_providers = [p for p in self.providers if p.is_available()]
        
        logger.info(f"TTS Engine initialized with {len(self.available_providers)} providers")
        for i, provider in enumerate(self.available_providers):
            logger.info(f"  {i+1}. {provider.__class__.__name__}")
    
    async def synthesize(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        """Synthesize speech using available providers with fallback"""
        
        if not self.available_providers:
            logger.error("No TTS providers available")
            return None
        
        # Clean text for better synthesis
        text = text.strip()
        if not text:
            return None
        
        # Remove excessive whitespace and special characters
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.,!?;:\-\'"]', '', text)
        
        for i, provider in enumerate(self.available_providers):
            try:
                result = await provider.synthesize(text, language, voice)
                if result and len(result) > 0:
                    if i > 0:  # Used fallback
                        logger.info(f"TTS fallback successful with {provider.__class__.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"TTS provider {provider.__class__.__name__} failed: {e}")
                continue
        
        logger.error("All TTS providers failed")
        return None
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        for provider in self.providers:
            status[provider.__class__.__name__] = {
                'available': provider.is_available(),
                'voices': provider.get_voices()[:5],  # First 5 voices
                'type': 'primary' if provider in self.available_providers[:1] else 'fallback'
            }
        return status
    
    def get_available_voices(self) -> Dict[str, list]:
        """Get all available voices from all providers"""
        voices = {}
        for provider in self.available_providers:
            voices[provider.__class__.__name__] = provider.get_voices()
        return voices 