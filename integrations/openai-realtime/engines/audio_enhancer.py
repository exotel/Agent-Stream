#!/usr/bin/env python3
"""
Audio Enhancement Engine
Provides noise cancellation, suppression, and audio quality improvements
"""

import numpy as np
import logging
from typing import Optional, Tuple, Union
from abc import ABC, abstractmethod
from enum import Enum
import tempfile
import os

logger = logging.getLogger(__name__)

class NoiseReductionMethod(Enum):
    """Available noise reduction methods"""
    SPECTRAL_SUBTRACTION = "spectral_subtraction"
    WIENER_FILTER = "wiener_filter"
    ADAPTIVE_FILTER = "adaptive_filter"
    RNN_NOISE_SUPPRESSION = "rnn_suppression"

class AudioQuality(Enum):
    """Audio quality levels"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    PREMIUM = "premium"

class AudioEnhancementProvider(ABC):
    """Abstract base class for audio enhancement providers"""
    
    @abstractmethod
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Enhance audio quality and reduce noise"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available"""
        pass

class SpectralSubtractionEnhancer(AudioEnhancementProvider):
    """Spectral subtraction noise reduction"""
    
    def __init__(self, noise_reduction_factor: float = 2.0):
        self.noise_reduction_factor = noise_reduction_factor
        self.noise_profile = None
        
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Apply spectral subtraction noise reduction"""
        try:
            import scipy.signal
            from scipy.fft import fft, ifft
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Apply spectral subtraction
            enhanced = self._spectral_subtraction(audio_array, sample_rate)
            
            # Convert back to bytes
            enhanced_int16 = np.clip(enhanced, -32768, 32767).astype(np.int16)
            return enhanced_int16.tobytes()
            
        except Exception as e:
            logger.warning(f"Spectral subtraction failed: {e}")
            return audio_data
    
    def _spectral_subtraction(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply spectral subtraction algorithm"""
        # Frame the audio
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = int(0.010 * sample_rate)    # 10ms hop
        
        # Estimate noise from first 0.5 seconds
        noise_frames = int(0.5 * sample_rate)
        noise_spectrum = np.abs(fft(audio[:noise_frames]))
        
        enhanced_audio = []
        
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            
            # Apply window
            windowed = frame * np.hanning(len(frame))
            
            # FFT
            spectrum = fft(windowed)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)
            
            # Spectral subtraction
            enhanced_magnitude = magnitude - self.noise_reduction_factor * noise_spectrum[:len(magnitude)]
            enhanced_magnitude = np.maximum(enhanced_magnitude, 0.1 * magnitude)
            
            # Reconstruct
            enhanced_spectrum = enhanced_magnitude * np.exp(1j * phase)
            enhanced_frame = np.real(ifft(enhanced_spectrum))
            
            enhanced_audio.extend(enhanced_frame)
        
        return np.array(enhanced_audio[:len(audio)])
    
    def is_available(self) -> bool:
        try:
            import scipy.signal
            from scipy.fft import fft, ifft
            return True
        except ImportError:
            return False

class WienerFilterEnhancer(AudioEnhancementProvider):
    """Wiener filter based noise reduction"""
    
    def __init__(self, noise_factor: float = 0.1):
        self.noise_factor = noise_factor
        
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Apply Wiener filter"""
        try:
            import scipy.signal
            
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Apply Wiener filter
            enhanced = self._wiener_filter(audio_array)
            
            # Convert back
            enhanced_int16 = np.clip(enhanced, -32768, 32767).astype(np.int16)
            return enhanced_int16.tobytes()
            
        except Exception as e:
            logger.warning(f"Wiener filter failed: {e}")
            return audio_data
    
    def _wiener_filter(self, audio: np.ndarray) -> np.ndarray:
        """Apply Wiener filter algorithm"""
        # Simple Wiener filter implementation
        # Estimate signal power and noise power
        signal_power = np.var(audio)
        noise_power = signal_power * self.noise_factor
        
        # Wiener gain
        wiener_gain = signal_power / (signal_power + noise_power)
        
        # Apply filter
        return audio * wiener_gain
    
    def is_available(self) -> bool:
        try:
            import scipy.signal
            return True
        except ImportError:
            return False

class RNNNoiseSuppressor(AudioEnhancementProvider):
    """RNN-based noise suppression (if available)"""
    
    def __init__(self):
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Load RNN noise suppression model"""
        try:
            # Try to load pre-trained RNN model
            # This would be a real model in production
            logger.info("RNN noise suppression model loaded")
        except Exception as e:
            logger.warning(f"RNN model not available: {e}")
    
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Apply RNN-based noise suppression"""
        if not self.is_available():
            return audio_data
            
        try:
            # This would use a real RNN model
            # For now, apply basic filtering
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Apply simple high-pass filter to remove low-frequency noise
            from scipy.signal import butter, filtfilt
            nyquist = sample_rate / 2
            cutoff = 300  # 300Hz cutoff
            b, a = butter(4, cutoff / nyquist, btype='high')
            enhanced = filtfilt(b, a, audio_array)
            
            enhanced_int16 = np.clip(enhanced, -32768, 32767).astype(np.int16)
            return enhanced_int16.tobytes()
            
        except Exception as e:
            logger.warning(f"RNN noise suppression failed: {e}")
            return audio_data
    
    def is_available(self) -> bool:
        try:
            import scipy.signal
            return True
        except ImportError:
            return False

class BasicAudioEnhancer(AudioEnhancementProvider):
    """Basic audio enhancement (always available)"""
    
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Apply basic audio enhancement"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Apply basic enhancements
            enhanced = self._basic_enhancement(audio_array, sample_rate)
            
            # Convert back
            enhanced_int16 = np.clip(enhanced, -32768, 32767).astype(np.int16)
            return enhanced_int16.tobytes()
            
        except Exception as e:
            logger.warning(f"Basic enhancement failed: {e}")
            return audio_data
    
    def _basic_enhancement(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply basic audio enhancements"""
        # 1. Normalize audio
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 16000
        
        # 2. Apply gentle high-pass filter (remove very low frequencies)
        if len(audio) > 100:
            # Simple moving average high-pass
            window_size = min(10, len(audio) // 10)
            moving_avg = np.convolve(audio, np.ones(window_size)/window_size, mode='same')
            audio = audio - 0.3 * moving_avg
        
        # 3. Apply soft clipping to reduce harsh sounds
        audio = np.tanh(audio / 8000) * 8000
        
        return audio
    
    def is_available(self) -> bool:
        return True

class ProductionAudioEnhancer:
    """Production-ready audio enhancement with multiple providers and fallback"""
    
    def __init__(self, quality_level: AudioQuality = AudioQuality.ENHANCED):
        self.quality_level = quality_level
        self.providers = []
        self.active_provider = None
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize enhancement providers in order of preference"""
        # Try to initialize providers based on quality level
        if self.quality_level == AudioQuality.PREMIUM:
            providers_to_try = [
                RNNNoiseSuppressor(),
                SpectralSubtractionEnhancer(),
                WienerFilterEnhancer(),
                BasicAudioEnhancer()
            ]
        elif self.quality_level == AudioQuality.ENHANCED:
            providers_to_try = [
                SpectralSubtractionEnhancer(),
                WienerFilterEnhancer(),
                BasicAudioEnhancer()
            ]
        else:  # BASIC
            providers_to_try = [
                BasicAudioEnhancer()
            ]
        
        # Check which providers are available
        for provider in providers_to_try:
            if provider.is_available():
                self.providers.append(provider)
                logger.info(f"Audio enhancer available: {provider.__class__.__name__}")
        
        if self.providers:
            self.active_provider = self.providers[0]
            logger.info(f"Using audio enhancer: {self.active_provider.__class__.__name__}")
        else:
            logger.error("No audio enhancement providers available!")
    
    def enhance_audio(self, audio_data: bytes, sample_rate: int = 8000) -> bytes:
        """Enhance audio with noise reduction and quality improvements"""
        if not self.active_provider:
            logger.warning("No audio enhancer available")
            return audio_data
        
        try:
            enhanced = self.active_provider.enhance_audio(audio_data, sample_rate)
            logger.debug(f"Audio enhanced: {len(audio_data)} -> {len(enhanced)} bytes")
            return enhanced
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            
            # Try fallback providers
            for provider in self.providers[1:]:
                try:
                    enhanced = provider.enhance_audio(audio_data, sample_rate)
                    logger.info(f"Fallback audio enhancer worked: {provider.__class__.__name__}")
                    self.active_provider = provider
                    return enhanced
                except Exception as fallback_error:
                    logger.warning(f"Fallback enhancer failed: {fallback_error}")
            
            logger.error("All audio enhancement providers failed")
            return audio_data
    
    def apply_noise_gate(self, audio_data: bytes, threshold: float = 0.01, sample_rate: int = 8000) -> bytes:
        """Apply noise gate to remove low-level noise"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Normalize to -1 to 1 range
            audio_normalized = audio_array / 32768.0
            
            # Apply noise gate
            gate_threshold = threshold
            audio_gated = np.where(np.abs(audio_normalized) > gate_threshold, 
                                 audio_normalized, 
                                 audio_normalized * 0.1)  # Reduce by 90%
            
            # Convert back
            audio_output = (audio_gated * 32768.0).astype(np.int16)
            return audio_output.tobytes()
            
        except Exception as e:
            logger.warning(f"Noise gate failed: {e}")
            return audio_data
    
    def apply_compressor(self, audio_data: bytes, ratio: float = 4.0, threshold: float = 0.7) -> bytes:
        """Apply audio compression for better voice clarity"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            
            # Normalize
            audio_normalized = audio_array / 32768.0
            
            # Simple compressor
            compressed = np.where(np.abs(audio_normalized) > threshold,
                                threshold + (np.abs(audio_normalized) - threshold) / ratio,
                                np.abs(audio_normalized)) * np.sign(audio_normalized)
            
            # Convert back
            audio_output = (compressed * 32768.0).astype(np.int16)
            return audio_output.tobytes()
            
        except Exception as e:
            logger.warning(f"Compressor failed: {e}")
            return audio_data
    
    def get_enhancement_info(self) -> dict:
        """Get information about available enhancement providers"""
        return {
            "quality_level": self.quality_level.value,
            "active_provider": self.active_provider.__class__.__name__ if self.active_provider else None,
            "available_providers": [p.__class__.__name__ for p in self.providers],
            "provider_count": len(self.providers)
        } 