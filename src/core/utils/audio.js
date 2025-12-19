const config = require('../config');

/**
 * Audio utility functions for handling PCM audio data
 * Format: 16-bit, 8/16/24 kHz, mono PCM (little-endian)
 */

class AudioUtils {
  /**
   * Validate chunk size for bidirectional streaming
   * @param {number} size - Chunk size in bytes
   * @returns {boolean} - Whether chunk size is valid
   */
  static validateChunkSize(size) {
    const { min, max, alignment } = config.chunkSize;

    if (size < min) {
      return { valid: false, reason: `Chunk size ${size} is below minimum ${min} bytes (100ms data)` };
    }

    if (size > max) {
      return { valid: false, reason: `Chunk size ${size} exceeds maximum ${max} bytes` };
    }

    if (size % alignment !== 0) {
      return {
        valid: false,
        reason: `Chunk size ${size} is not a multiple of ${alignment} bytes. This may cause audio gaps.`
      };
    }

    return { valid: true };
  }

  /**
   * Convert base64 encoded audio to Buffer
   * @param {string} base64Audio - Base64 encoded audio
   * @returns {Buffer} - Audio buffer
   */
  static decodeAudio(base64Audio) {
    return Buffer.from(base64Audio, 'base64');
  }

  /**
   * Convert audio buffer to base64
   * @param {Buffer} audioBuffer - Audio buffer
   * @returns {string} - Base64 encoded audio
   */
  static encodeAudio(audioBuffer) {
    return audioBuffer.toString('base64');
  }

  /**
   * Calculate duration of audio chunk in milliseconds
   * @param {number} bytes - Size in bytes
   * @param {number} sampleRate - Sample rate (8000, 16000, 24000)
   * @returns {number} - Duration in milliseconds
   */
  static calculateDuration(bytes, sampleRate = 8000) {
    // 16-bit = 2 bytes per sample, mono
    const samples = bytes / 2;
    return (samples / sampleRate) * 1000;
  }

  /**
   * Calculate bytes needed for a duration
   * @param {number} durationMs - Duration in milliseconds
   * @param {number} sampleRate - Sample rate (8000, 16000, 24000)
   * @returns {number} - Bytes needed
   */
  static calculateBytesForDuration(durationMs, sampleRate = 8000) {
    const samples = (durationMs / 1000) * sampleRate;
    return Math.floor(samples) * 2; // 2 bytes per sample (16-bit)
  }

  /**
   * Generate silence buffer
   * @param {number} durationMs - Duration in milliseconds
   * @param {number} sampleRate - Sample rate
   * @returns {Buffer} - Silence buffer
   */
  static generateSilence(durationMs, sampleRate = 8000) {
    const bytes = this.calculateBytesForDuration(durationMs, sampleRate);
    return Buffer.alloc(bytes, 0);
  }

  /**
   * Create a simple tone (for testing)
   * @param {number} frequency - Frequency in Hz
   * @param {number} durationMs - Duration in milliseconds
   * @param {number} sampleRate - Sample rate
   * @returns {Buffer} - Audio buffer with tone
   */
  static generateTone(frequency, durationMs, sampleRate = 8000) {
    const bytes = this.calculateBytesForDuration(durationMs, sampleRate);
    const samples = bytes / 2;
    const buffer = Buffer.alloc(bytes);

    for (let i = 0; i < samples; i++) {
      // Generate sine wave
      const sample = Math.sin(2 * Math.PI * frequency * i / sampleRate);
      // Convert to 16-bit integer (-32768 to 32767)
      const value = Math.floor(sample * 32767);
      // Write as little-endian 16-bit
      buffer.writeInt16LE(value, i * 2);
    }

    return buffer;
  }

  /**
   * Mix two audio buffers
   * @param {Buffer} buffer1 - First audio buffer
   * @param {Buffer} buffer2 - Second audio buffer
   * @returns {Buffer} - Mixed audio buffer
   */
  static mixAudio(buffer1, buffer2) {
    const length = Math.max(buffer1.length, buffer2.length);
    const result = Buffer.alloc(length);

    for (let i = 0; i < length; i += 2) {
      const sample1 = i < buffer1.length ? buffer1.readInt16LE(i) : 0;
      const sample2 = i < buffer2.length ? buffer2.readInt16LE(i) : 0;

      // Mix with simple averaging
      const mixed = Math.floor((sample1 + sample2) / 2);
      result.writeInt16LE(mixed, i);
    }

    return result;
  }

  /**
   * Validate sample rate
   * @param {number} sampleRate - Sample rate to validate
   * @returns {boolean} - Whether sample rate is supported
   */
  static validateSampleRate(sampleRate) {
    return config.audio.supportedSampleRates.includes(sampleRate);
  }
}

module.exports = AudioUtils;

