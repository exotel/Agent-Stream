/**
 * Audio Resampler Utility
 *
 * Handles sample rate conversion for audio buffers
 * - Exotel sends: 8kHz PCM
 * - Some services need: 16kHz, 24kHz
 * - Automatic conversion both ways
 */

const Logger = require('./logger');
const logger = new Logger('RESAMPLER');

class AudioResampler {
  /**
   * Resample PCM audio buffer
   *
   * @param {Buffer} inputBuffer - Input PCM audio
   * @param {number} fromRate - Source sample rate (e.g., 8000)
   * @param {number} toRate - Target sample rate (e.g., 16000)
   * @returns {Buffer} - Resampled PCM audio
   */
  static resample(inputBuffer, fromRate, toRate) {
    // No conversion needed
    if (fromRate === toRate) {
      return inputBuffer;
    }

    try {
      // Calculate ratio
      const ratio = toRate / fromRate;

      // Convert buffer to 16-bit samples
      const inputSamples = new Int16Array(
        inputBuffer.buffer,
        inputBuffer.byteOffset,
        inputBuffer.length / 2
      );

      // Calculate output size
      const outputLength = Math.floor(inputSamples.length * ratio);
      const outputSamples = new Int16Array(outputLength);

      if (ratio > 1) {
        // Upsampling (e.g., 8kHz -> 16kHz)
        this.upsample(inputSamples, outputSamples, ratio);
      } else {
        // Downsampling (e.g., 16kHz -> 8kHz)
        this.downsample(inputSamples, outputSamples, ratio);
      }

      // Convert back to Buffer
      const outputBuffer = Buffer.from(outputSamples.buffer);

      logger.debug(`Resampled: ${fromRate}Hz -> ${toRate}Hz (${inputBuffer.length} -> ${outputBuffer.length} bytes)`);

      return outputBuffer;
    } catch (error) {
      logger.error('Resampling error:', error.message);
      return inputBuffer; // Return original on error
    }
  }

  /**
   * Upsample audio (increase sample rate)
   * Uses linear interpolation
   */
  static upsample(input, output, ratio) {
    for (let i = 0; i < output.length; i++) {
      const srcIndex = i / ratio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, input.length - 1);
      const fraction = srcIndex - srcIndexFloor;

      // Linear interpolation
      output[i] = Math.round(
        input[srcIndexFloor] * (1 - fraction) +
        input[srcIndexCeil] * fraction
      );
    }
  }

  /**
   * Downsample audio (decrease sample rate)
   * Uses simple averaging (anti-aliasing)
   */
  static downsample(input, output, ratio) {
    const windowSize = Math.floor(1 / ratio);

    for (let i = 0; i < output.length; i++) {
      const srcStart = Math.floor(i / ratio);
      const srcEnd = Math.min(srcStart + windowSize, input.length);

      // Average samples in window
      let sum = 0;
      let count = 0;
      for (let j = srcStart; j < srcEnd; j++) {
        sum += input[j];
        count++;
      }

      output[i] = count > 0 ? Math.round(sum / count) : 0;
    }
  }

  /**
   * Resample to common sample rates
   */
  static to8kHz(buffer, fromRate) {
    return this.resample(buffer, fromRate, 8000);
  }

  static to16kHz(buffer, fromRate) {
    return this.resample(buffer, fromRate, 16000);
  }

  static to24kHz(buffer, fromRate) {
    return this.resample(buffer, fromRate, 24000);
  }

  /**
   * Get sample count from buffer
   */
  static getSampleCount(buffer) {
    return buffer.length / 2; // 16-bit = 2 bytes per sample
  }

  /**
   * Get duration in milliseconds
   */
  static getDuration(buffer, sampleRate) {
    const samples = this.getSampleCount(buffer);
    return (samples / sampleRate) * 1000;
  }

  /**
   * Validate audio buffer
   */
  static isValidPCM(buffer) {
    if (!Buffer.isBuffer(buffer)) return false;
    if (buffer.length === 0) return false;
    if (buffer.length % 2 !== 0) return false; // Must be even (16-bit)
    return true;
  }
}

module.exports = AudioResampler;

