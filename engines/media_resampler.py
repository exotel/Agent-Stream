"""
Production-ready Media Resampler
Handles audio upsampling/downsampling for different sample rates
"""

import logging
import numpy as np
from typing import Optional, Tuple
from enum import Enum
import config

logger = logging.getLogger(__name__)

class SampleRate(Enum):
    """Supported sample rates"""
    RATE_8K = 8000
    RATE_16K = 16000
    RATE_24K = 24000
    RATE_44K = 44100
    RATE_48K = 48000

class AudioFormat(Enum):
    """Supported audio formats"""
    PCM_16 = 16
    PCM_24 = 24
    PCM_32 = 32

class MediaResampler:
    """Production media resampler with multiple algorithms"""
    
    def __init__(self):
        self.resampler_backend = getattr(config, 'RESAMPLER_BACKEND', 'scipy')
        self.quality = getattr(config, 'RESAMPLER_QUALITY', 'medium')
        logger.info(f"MediaResampler initialized with {self.resampler_backend} backend")
    
    def resample_audio(
        self, 
        audio_data: bytes, 
        from_rate: int, 
        to_rate: int,
        channels: int = 1,
        sample_width: int = 2
    ) -> Optional[bytes]:
        """
        Resample audio data from one sample rate to another
        
        Args:
            audio_data: Raw audio bytes
            from_rate: Source sample rate
            to_rate: Target sample rate
            channels: Number of audio channels
            sample_width: Sample width in bytes (2=16bit, 3=24bit, 4=32bit)
        
        Returns:
            Resampled audio bytes or None if failed
        """
        if from_rate == to_rate:
            return audio_data
        
        try:
            if self.resampler_backend == 'scipy':
                return self._resample_scipy(audio_data, from_rate, to_rate, channels, sample_width)
            elif self.resampler_backend == 'librosa':
                return self._resample_librosa(audio_data, from_rate, to_rate, channels, sample_width)
            else:
                return self._resample_pydub(audio_data, from_rate, to_rate, channels, sample_width)
                
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            return None
    
    def _resample_scipy(
        self, 
        audio_data: bytes, 
        from_rate: int, 
        to_rate: int,
        channels: int,
        sample_width: int
    ) -> Optional[bytes]:
        """Resample using SciPy (high quality)"""
        try:
            from scipy import signal
            
            # Convert bytes to numpy array
            if sample_width == 2:  # 16-bit
                dtype = np.int16
            elif sample_width == 3:  # 24-bit (convert to 32-bit)
                dtype = np.int32
                audio_data = self._convert_24bit_to_32bit(audio_data)
                sample_width = 4
            else:  # 32-bit
                dtype = np.int32
            
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Handle multi-channel audio
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)
                resampled_channels = []
                
                for ch in range(channels):
                    channel_data = audio_array[:, ch]
                    resampled_channel = signal.resample(
                        channel_data, 
                        int(len(channel_data) * to_rate / from_rate)
                    )
                    resampled_channels.append(resampled_channel)
                
                resampled_audio = np.column_stack(resampled_channels)
            else:
                resampled_audio = signal.resample(
                    audio_array, 
                    int(len(audio_array) * to_rate / from_rate)
                )
            
            # Convert back to original bit depth
            if sample_width == 4 and dtype == np.int32:
                resampled_audio = resampled_audio.astype(np.int32)
            else:
                resampled_audio = resampled_audio.astype(dtype)
            
            # Convert back to 24-bit if needed
            if sample_width == 4 and dtype == np.int32:
                result_bytes = self._convert_32bit_to_24bit(resampled_audio.tobytes())
            else:
                result_bytes = resampled_audio.tobytes()
            
            logger.debug(f"SciPy resampling: {from_rate}Hz -> {to_rate}Hz, {len(audio_data)} -> {len(result_bytes)} bytes")
            return result_bytes
            
        except ImportError:
            logger.warning("SciPy not available, falling back to pydub")
            return self._resample_pydub(audio_data, from_rate, to_rate, channels, sample_width)
        except Exception as e:
            logger.error(f"SciPy resampling error: {e}")
            return None
    
    def _resample_librosa(
        self, 
        audio_data: bytes, 
        from_rate: int, 
        to_rate: int,
        channels: int,
        sample_width: int
    ) -> Optional[bytes]:
        """Resample using librosa (music/audio optimized)"""
        try:
            import librosa
            
            # Convert bytes to float array for librosa
            if sample_width == 2:
                dtype = np.int16
                max_val = 32767.0
            elif sample_width == 3:
                audio_data = self._convert_24bit_to_32bit(audio_data)
                dtype = np.int32
                max_val = 2147483647.0
                sample_width = 4
            else:
                dtype = np.int32
                max_val = 2147483647.0
            
            audio_array = np.frombuffer(audio_data, dtype=dtype).astype(np.float32) / max_val
            
            # Handle multi-channel
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels).T
                resampled_audio = librosa.resample(
                    audio_array, 
                    orig_sr=from_rate, 
                    target_sr=to_rate,
                    res_type='kaiser_best' if self.quality == 'high' else 'kaiser_fast'
                )
                resampled_audio = resampled_audio.T
            else:
                resampled_audio = librosa.resample(
                    audio_array, 
                    orig_sr=from_rate, 
                    target_sr=to_rate,
                    res_type='kaiser_best' if self.quality == 'high' else 'kaiser_fast'
                )
            
            # Convert back to integer
            resampled_audio = (resampled_audio * max_val).astype(dtype)
            
            # Convert back to 24-bit if needed
            if sample_width == 4 and dtype == np.int32:
                result_bytes = self._convert_32bit_to_24bit(resampled_audio.tobytes())
            else:
                result_bytes = resampled_audio.tobytes()
            
            logger.debug(f"Librosa resampling: {from_rate}Hz -> {to_rate}Hz, {len(audio_data)} -> {len(result_bytes)} bytes")
            return result_bytes
            
        except ImportError:
            logger.warning("Librosa not available, falling back to pydub")
            return self._resample_pydub(audio_data, from_rate, to_rate, channels, sample_width)
        except Exception as e:
            logger.error(f"Librosa resampling error: {e}")
            return None
    
    def _resample_pydub(
        self, 
        audio_data: bytes, 
        from_rate: int, 
        to_rate: int,
        channels: int,
        sample_width: int
    ) -> Optional[bytes]:
        """Resample using pydub (fallback)"""
        try:
            from pydub import AudioSegment
            
            # Create AudioSegment
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=sample_width,
                frame_rate=from_rate,
                channels=channels
            )
            
            # Resample
            resampled_segment = audio_segment.set_frame_rate(to_rate)
            
            # Export as raw data
            result_bytes = resampled_segment.raw_data
            
            logger.debug(f"Pydub resampling: {from_rate}Hz -> {to_rate}Hz, {len(audio_data)} -> {len(result_bytes)} bytes")
            return result_bytes
            
        except Exception as e:
            logger.error(f"Pydub resampling error: {e}")
            return None
    
    def _convert_24bit_to_32bit(self, audio_24bit: bytes) -> bytes:
        """Convert 24-bit audio to 32-bit for processing"""
        # 24-bit audio is stored as 3 bytes per sample
        samples_24bit = []
        for i in range(0, len(audio_24bit), 3):
            if i + 2 < len(audio_24bit):
                # Extract 3 bytes and convert to 32-bit signed integer
                sample_bytes = audio_24bit[i:i+3]
                # Add padding byte (MSB) for 32-bit
                sample_32bit = sample_bytes + b'\x00'
                sample_int = int.from_bytes(sample_32bit, byteorder='little', signed=True)
                samples_24bit.append(sample_int)
        
        return np.array(samples_24bit, dtype=np.int32).tobytes()
    
    def _convert_32bit_to_24bit(self, audio_32bit: bytes) -> bytes:
        """Convert 32-bit audio back to 24-bit"""
        audio_array = np.frombuffer(audio_32bit, dtype=np.int32)
        
        # Convert each 32-bit sample to 24-bit (3 bytes)
        result = bytearray()
        for sample in audio_array:
            # Convert to bytes and take first 3 bytes (drop MSB)
            sample_bytes = sample.to_bytes(4, byteorder='little', signed=True)
            result.extend(sample_bytes[:3])
        
        return bytes(result)
    
    def convert_format(
        self, 
        audio_data: bytes, 
        from_format: AudioFormat, 
        to_format: AudioFormat,
        sample_rate: int,
        channels: int = 1
    ) -> Optional[bytes]:
        """Convert between different audio bit depths"""
        if from_format == to_format:
            return audio_data
        
        try:
            from pydub import AudioSegment
            
            # Create AudioSegment
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=from_format.value // 8,
                frame_rate=sample_rate,
                channels=channels
            )
            
            # Convert bit depth
            if to_format == AudioFormat.PCM_16:
                converted_segment = audio_segment.set_sample_width(2)
            elif to_format == AudioFormat.PCM_24:
                converted_segment = audio_segment.set_sample_width(3)
            else:  # PCM_32
                converted_segment = audio_segment.set_sample_width(4)
            
            return converted_segment.raw_data
            
        except Exception as e:
            logger.error(f"Format conversion error: {e}")
            return None
    
    def get_audio_info(self, audio_data: bytes, sample_width: int, channels: int) -> dict:
        """Get information about audio data"""
        samples_per_channel = len(audio_data) // (sample_width * channels)
        
        return {
            'total_bytes': len(audio_data),
            'sample_width': sample_width,
            'channels': channels,
            'samples_per_channel': samples_per_channel,
            'bit_depth': sample_width * 8,
            'duration_samples': samples_per_channel
        }
    
    def resample_for_exotel(self, audio_data: bytes, from_rate: int) -> bytes:
        """Convenience method to resample audio for Exotel (8kHz, 16-bit, mono)"""
        target_rate = getattr(config, 'EXOTEL_SAMPLE_RATE', 8000)
        
        resampled = self.resample_audio(
            audio_data=audio_data,
            from_rate=from_rate,
            to_rate=target_rate,
            channels=1,
            sample_width=2
        )
        
        return resampled if resampled else audio_data
    
    def normalize_audio_levels(self, audio_data: bytes, sample_width: int = 2) -> bytes:
        """Normalize audio levels to prevent clipping"""
        try:
            if sample_width == 2:
                dtype = np.int16
                max_val = 32767
            elif sample_width == 3:
                audio_data = self._convert_24bit_to_32bit(audio_data)
                dtype = np.int32
                max_val = 2147483647
                sample_width = 4
            else:
                dtype = np.int32
                max_val = 2147483647
            
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Find peak amplitude
            peak = np.max(np.abs(audio_array))
            
            if peak > 0:
                # Normalize to 90% of max to prevent clipping
                normalization_factor = (max_val * 0.9) / peak
                if normalization_factor < 1.0:  # Only normalize if too loud
                    audio_array = (audio_array * normalization_factor).astype(dtype)
            
            # Convert back to original format
            if sample_width == 4 and dtype == np.int32:
                return self._convert_32bit_to_24bit(audio_array.tobytes())
            else:
                return audio_array.tobytes()
                
        except Exception as e:
            logger.error(f"Audio normalization error: {e}")
            return audio_data 