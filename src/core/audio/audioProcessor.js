const Logger = require('../utils/logger');
const AudioUtils = require('../utils/audio');
const config = require('../config');
const RNNoiseProcessor = require('./rnnoiseProcessor');
const SpectralProcessor = require('./spectralProcessor');

/**
 * Audio Processing Pipeline with Integrated Noise Cancellation
 *
 * Supports:
 * - RNNoise (open source, deep learning-based)
 * - Spectral Subtraction (free, no dependencies)
 *
 * Modes:
 * - both: Process incoming and outgoing audio
 * - incoming_only: Only process audio from caller
 * - outgoing_only: Only process audio to caller
 * - disabled: Passthrough (no processing)
 */

class AudioProcessor {
  constructor(streamId, configOverride = {}) {
    this.streamId = streamId;
    this.logger = new Logger(`AUDIO-PROC-${streamId.substring(0, 8)}`);

    // Merge configuration
    this.config = {
      enableNoiseCancellation: config.noiseCancellation.enabled,
      processorType: config.noiseCancellation.processorType,
      processingMode: config.noiseCancellation.mode,
      enableAGC: false,
      sampleRate: configOverride.sampleRate || 8000,
      maxLatency: config.noiseCancellation.maxLatencyMs,
      enableStats: config.noiseCancellation.enableStats,
      ...configOverride
    };

    this.noiseCancellationSDK = null;
    this.initializationPromise = null;
    this.processingStats = {
      incoming: { count: 0, totalTime: 0, avgLatency: 0 },
      outgoing: { count: 0, totalTime: 0, avgLatency: 0 }
    };

    // Start initialization asynchronously
    this.initializationPromise = this.initializeSDKs();
  }

  /**
   * Initialize audio processing SDKs
   */
  async initializeSDKs() {
    if (!this.config.enableNoiseCancellation || this.config.processingMode === 'disabled') {
      this.logger.info('Noise cancellation disabled');
      return;
    }

    try {
      this.logger.info(`Initializing ${this.config.processorType} noise processor...`);
      this.logger.info(`Processing mode: ${this.config.processingMode}`);

      // Create appropriate processor
      switch (this.config.processorType) {
        case 'rnnoise':
          this.noiseCancellationSDK = new RNNoiseProcessor(this.streamId, {
            sampleRate: this.config.sampleRate,
            maxLatency: this.config.maxLatency
          });
          break;

        case 'spectral':
          this.noiseCancellationSDK = new SpectralProcessor(this.streamId, {
            sampleRate: this.config.sampleRate
          });
          break;

        default:
          this.logger.warn(`Unknown processor type: ${this.config.processorType}, using spectral`);
          this.noiseCancellationSDK = new SpectralProcessor(this.streamId, {
            sampleRate: this.config.sampleRate
          });
      }

      // Initialize the processor
      const success = await this.noiseCancellationSDK.initialize();

      if (success) {
        this.logger.info(`✓ ${this.config.processorType} initialized successfully`);
        this.logger.info(`  Max latency threshold: ${this.config.maxLatency}ms`);
      } else {
        this.logger.warn('Failed to initialize noise processor, using passthrough');
        this.noiseCancellationSDK = null;
      }

    } catch (error) {
      this.logger.error('Error initializing noise processor:', error.message);
      this.noiseCancellationSDK = null;
    }
  }

  /**
   * Process incoming audio from caller
   *
   * This is called BEFORE:
   * - Speech-to-text
   * - Audio analysis
   * - Any AI processing
   *
   * @param {Buffer} audioBuffer - Raw PCM audio from caller
   * @returns {Buffer} - Processed audio
   */
  async processIncomingAudio(audioBuffer) {
    const startTime = Date.now();

    try {
      // Wait for initialization to complete
      if (this.initializationPromise) {
        await this.initializationPromise;
        this.initializationPromise = null;
      }

      let processedBuffer = audioBuffer;

      // Check if incoming processing is enabled
      const shouldProcess = this.config.enableNoiseCancellation &&
                           (this.config.processingMode === 'both' ||
                            this.config.processingMode === 'incoming_only');

      // 1. Noise Cancellation
      if (shouldProcess && this.noiseCancellationSDK) {
        processedBuffer = await this.applyNoiseCancellation(
          processedBuffer,
          'incoming'
        );
      }

      // 2. Automatic Gain Control (normalize volume)
      if (this.config.enableAGC) {
        processedBuffer = this.applyAGC(processedBuffer);
      }

      // Update stats
      const processingTime = Date.now() - startTime;
      this.updateStats('incoming', processingTime);

      if (this.config.enableStats && processingTime > this.config.maxLatency) {
        this.logger.warn(`⚠️  Incoming audio processing took ${processingTime}ms (threshold: ${this.config.maxLatency}ms)`);
      }

      return processedBuffer;

    } catch (error) {
      this.logger.error('Error processing incoming audio:', error.message);
      return audioBuffer; // Return original on error
    }
  }

  /**
   * Process outgoing audio to caller
   *
   * This is called BEFORE sending to Exotel:
   * - After TTS generation
   * - After audio file playback
   *
   * @param {Buffer} audioBuffer - Audio to send to caller
   * @returns {Buffer} - Processed audio
   */
  async processOutgoingAudio(audioBuffer) {
    const startTime = Date.now();

    try {
      // Wait for initialization to complete
      if (this.initializationPromise) {
        await this.initializationPromise;
        this.initializationPromise = null;
      }

      let processedBuffer = audioBuffer;

      // Check if outgoing processing is enabled
      const shouldProcess = this.config.enableNoiseCancellation &&
                           (this.config.processingMode === 'both' ||
                            this.config.processingMode === 'outgoing_only');

      // 1. Noise Cancellation (if TTS/recordings have noise)
      if (shouldProcess && this.noiseCancellationSDK) {
        processedBuffer = await this.applyNoiseCancellation(
          processedBuffer,
          'outgoing'
        );
      }

      // 2. Ensure proper format
      processedBuffer = this.ensureProperFormat(processedBuffer);

      // Update stats
      const processingTime = Date.now() - startTime;
      this.updateStats('outgoing', processingTime);

      if (this.config.enableStats && processingTime > this.config.maxLatency) {
        this.logger.warn(`⚠️  Outgoing audio processing took ${processingTime}ms (threshold: ${this.config.maxLatency}ms)`);
      }

      return processedBuffer;

    } catch (error) {
      this.logger.error('Error processing outgoing audio:', error.message);
      return audioBuffer;
    }
  }

  /**
   * Apply noise cancellation using configured SDK
   *
   * @param {Buffer} audioBuffer - Audio to process
   * @param {string} direction - 'incoming' or 'outgoing'
   * @returns {Buffer} - Processed audio
   */
  async applyNoiseCancellation(audioBuffer, direction = 'incoming') {
    if (!this.noiseCancellationSDK) {
      return audioBuffer;
    }

    const startTime = Date.now();

    try {
      // Process with the configured SDK
      const processed = await this.noiseCancellationSDK.process(
        audioBuffer,
        this.config.sampleRate
      );

      const duration = Date.now() - startTime;

      if (this.config.enableStats && duration > 10) {
        this.logger.debug(`Noise cancellation (${direction}) took ${duration}ms`);
      }

      return processed;

    } catch (error) {
      this.logger.error(`Noise cancellation error (${direction}):`, error.message);
      return audioBuffer;
    }
  }

  /**
   * Update processing statistics
   */
  updateStats(direction, processingTime) {
    const stats = this.processingStats[direction];
    stats.count++;
    stats.totalTime += processingTime;
    stats.avgLatency = stats.totalTime / stats.count;

    // Log every 100 frames
    if (this.config.enableStats && stats.count % 100 === 0) {
      this.logger.info(`📊 ${direction} stats: avg latency ${stats.avgLatency.toFixed(2)}ms (${stats.count} frames)`);
    }
  }

  /**
   * Apply Automatic Gain Control (volume normalization)
   */
  applyAGC(audioBuffer) {
    try {
      // Calculate current RMS level
      let sumSquares = 0;
      for (let i = 0; i < audioBuffer.length; i += 2) {
        const sample = audioBuffer.readInt16LE(i);
        sumSquares += sample * sample;
      }
      const rms = Math.sqrt(sumSquares / (audioBuffer.length / 2));

      // Target RMS level (adjust as needed)
      const targetRMS = 3000;

      if (rms > 0) {
        const gain = targetRMS / rms;
        const limitedGain = Math.min(Math.max(gain, 0.5), 2.0); // Limit gain

        // Apply gain
        const normalized = Buffer.alloc(audioBuffer.length);
        for (let i = 0; i < audioBuffer.length; i += 2) {
          const sample = audioBuffer.readInt16LE(i);
          const amplified = Math.round(sample * limitedGain);
          // Clamp to prevent clipping
          const clamped = Math.min(Math.max(amplified, -32768), 32767);
          normalized.writeInt16LE(clamped, i);
        }

        return normalized;
      }

      return audioBuffer;
    } catch (error) {
      this.logger.error('Error applying AGC:', error.message);
      return audioBuffer;
    }
  }

  /**
   * Ensure audio buffer is in proper format
   */
  ensureProperFormat(audioBuffer) {
    // Validate chunk size
    const validation = AudioUtils.validateChunkSize(audioBuffer.length);
    if (!validation.valid) {
      this.logger.warn(validation.reason);

      // Pad or trim to nearest valid size
      const targetSize = Math.floor(audioBuffer.length / 320) * 320;
      if (targetSize !== audioBuffer.length) {
        return audioBuffer.slice(0, targetSize);
      }
    }

    return audioBuffer;
  }

  /**
   * Batch process audio chunks
   * Useful for processing multiple chunks at once for efficiency
   */
  async processBatch(audioBuffers) {
    const processed = [];

    for (const buffer of audioBuffers) {
      processed.push(await this.processIncomingAudio(buffer));
    }

    return processed;
  }

  /**
   * Get processing statistics
   */
  getStats() {
    const sdkStats = this.noiseCancellationSDK?.getStats?.() || {};

    return {
      streamId: this.streamId,
      config: {
        processorType: this.config.processorType,
        processingMode: this.config.processingMode,
        enabled: this.config.enableNoiseCancellation,
        sampleRate: this.config.sampleRate
      },
      sdkInitialized: this.noiseCancellationSDK !== null,
      processing: this.processingStats,
      sdk: sdkStats
    };
  }

  /**
   * Cleanup resources
   */
  async destroy() {
    this.logger.info('Cleaning up audio processor');

    // Log final statistics
    if (this.config.enableStats) {
      const stats = this.getStats();
      this.logger.info('📊 Final processing statistics:', {
        incoming: `${stats.processing.incoming.count} frames, avg ${stats.processing.incoming.avgLatency.toFixed(2)}ms`,
        outgoing: `${stats.processing.outgoing.count} frames, avg ${stats.processing.outgoing.avgLatency.toFixed(2)}ms`
      });
    }

    // Cleanup SDK resources
    if (this.noiseCancellationSDK?.destroy) {
      await this.noiseCancellationSDK.destroy();
    }

    this.noiseCancellationSDK = null;
  }
}

module.exports = AudioProcessor;

