/**
 * RNNoise Processor - Open Source Noise Suppression
 *
 * RNNoise is a lightweight noise suppression library using deep learning
 * https://github.com/xiph/rnnoise
 *
 * Performance: ~5-10ms latency per frame
 * Quality: Very good for voice
 */

const Logger = require('../utils/logger');

class RNNoiseProcessor {
  constructor(streamId, config = {}) {
    this.streamId = streamId;
    this.logger = new Logger(`RNNOISE-${streamId.substring(0, 8)}`);
    this.config = {
      sampleRate: config.sampleRate || 48000, // RNNoise works at 48kHz
      frameSamples: 480, // 10ms at 48kHz
      ...config
    };

    this.initialized = false;
    this.noiseSupressor = null;
    this.processingStats = {
      totalFrames: 0,
      totalTime: 0,
      avgLatency: 0
    };
  }

  /**
   * Initialize RNNoise processor
   */
  async initialize() {
    try {
      this.logger.info('Initializing RNNoise processor...');

      // Import the noise suppressor
      const { NoiseSuppressor } = require('@sapphi-red/web-noise-suppressor');

      // Create instance
      this.noiseSupressor = await NoiseSuppressor.create();

      this.initialized = true;
      this.logger.info('✓ RNNoise processor initialized successfully');

      return true;
    } catch (error) {
      this.logger.error('Failed to initialize RNNoise:', error.message);
      this.logger.warn('Falling back to passthrough mode (no noise cancellation)');
      this.initialized = false;
      return false;
    }
  }

  /**
   * Process audio buffer with RNNoise
   *
   * @param {Buffer} audioBuffer - PCM audio (16-bit, little-endian)
   * @param {number} originalSampleRate - Original sample rate (8000, 16000, etc.)
   * @returns {Buffer} - Processed audio at original sample rate
   */
  async process(audioBuffer, originalSampleRate = 8000) {
    if (!this.initialized || !this.noiseSupressor) {
      return audioBuffer; // Passthrough if not initialized
    }

    try {
      const startTime = Date.now();

      // Convert Buffer to Float32Array (RNNoise expects float samples)
      const float32Samples = this.bufferToFloat32(audioBuffer);

      // Resample to 48kHz if needed (RNNoise requirement)
      let samples48k = float32Samples;
      if (originalSampleRate !== 48000) {
        samples48k = this.resample(float32Samples, originalSampleRate, 48000);
      }

      // Process in 480-sample frames (10ms at 48kHz)
      const processedFrames = [];
      const frameSize = 480;

      for (let i = 0; i < samples48k.length; i += frameSize) {
        const frame = samples48k.slice(i, i + frameSize);

        // Pad last frame if needed
        if (frame.length < frameSize) {
          const padded = new Float32Array(frameSize);
          padded.set(frame);
          processedFrames.push(await this.noiseSupressor.process(padded));
        } else {
          processedFrames.push(await this.noiseSupressor.process(frame));
        }
      }

      // Concatenate processed frames
      let processedSamples = new Float32Array(
        processedFrames.reduce((acc, frame) => acc + frame.length, 0)
      );
      let offset = 0;
      for (const frame of processedFrames) {
        processedSamples.set(frame, offset);
        offset += frame.length;
      }

      // Resample back to original sample rate if needed
      if (originalSampleRate !== 48000) {
        processedSamples = this.resample(processedSamples, 48000, originalSampleRate);
      }

      // Convert back to Buffer
      const outputBuffer = this.float32ToBuffer(processedSamples);

      // Update statistics
      const processingTime = Date.now() - startTime;
      this.updateStats(processingTime);

      if (processingTime > this.config.maxLatency) {
        this.logger.warn(`High latency: ${processingTime}ms (threshold: ${this.config.maxLatency}ms)`);
      }

      return outputBuffer;

    } catch (error) {
      this.logger.error('Error processing with RNNoise:', error.message);
      return audioBuffer; // Return original on error
    }
  }

  /**
   * Convert Buffer (16-bit PCM) to Float32Array (-1.0 to 1.0)
   */
  bufferToFloat32(buffer) {
    const samples = new Float32Array(buffer.length / 2);
    for (let i = 0; i < samples.length; i++) {
      const int16 = buffer.readInt16LE(i * 2);
      samples[i] = int16 / 32768.0; // Normalize to -1.0 to 1.0
    }
    return samples;
  }

  /**
   * Convert Float32Array to Buffer (16-bit PCM)
   */
  float32ToBuffer(samples) {
    const buffer = Buffer.alloc(samples.length * 2);
    for (let i = 0; i < samples.length; i++) {
      const int16 = Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32768)));
      buffer.writeInt16LE(int16, i * 2);
    }
    return buffer;
  }

  /**
   * Simple linear resampling
   * For better quality, use a proper resampling library
   */
  resample(samples, fromRate, toRate) {
    if (fromRate === toRate) return samples;

    const ratio = fromRate / toRate;
    const outputLength = Math.floor(samples.length / ratio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, samples.length - 1);
      const fraction = srcIndex - srcIndexFloor;

      // Linear interpolation
      output[i] = samples[srcIndexFloor] * (1 - fraction) +
                  samples[srcIndexCeil] * fraction;
    }

    return output;
  }

  /**
   * Update processing statistics
   */
  updateStats(processingTime) {
    this.processingStats.totalFrames++;
    this.processingStats.totalTime += processingTime;
    this.processingStats.avgLatency =
      this.processingStats.totalTime / this.processingStats.totalFrames;
  }

  /**
   * Get processing statistics
   */
  getStats() {
    return {
      ...this.processingStats,
      initialized: this.initialized
    };
  }

  /**
   * Cleanup resources
   */
  async destroy() {
    if (this.noiseSupressor) {
      try {
        await this.noiseSupressor.destroy();
        this.logger.info('RNNoise processor destroyed');
      } catch (error) {
        this.logger.error('Error destroying RNNoise:', error.message);
      }
    }
    this.noiseSupressor = null;
    this.initialized = false;
  }
}

module.exports = RNNoiseProcessor;

