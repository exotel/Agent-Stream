/**
 * Speech-to-Text Service
 * Unified interface for multiple STT providers
 */

const Logger = require('../utils/logger');
const aiConfig = require('../../config/ai-services.config');

class STTService {
  constructor(provider = null) {
    this.provider = provider || aiConfig.stt.provider;
    this.config = aiConfig.stt[this.provider];
    this.logger = new Logger(`STT-${this.provider.toUpperCase()}`);
    this.adapter = null;

    this.initialize();
  }

  /**
   * Initialize STT adapter based on provider
   */
  initialize() {
    this.logger.info(`Initializing ${this.provider} STT service...`);

    try {
      switch (this.provider) {
        case 'deepgram':
          this.adapter = require('./adapters/stt/deepgramAdapter');
          break;
        case 'whisper':
          this.adapter = require('./adapters/stt/whisperAdapter');
          break;
        case 'google':
          this.adapter = require('./adapters/stt/googleSTTAdapter');
          break;
        case 'azure':
          this.adapter = require('./adapters/stt/azureSTTAdapter');
          break;
        case 'assemblyai':
          this.adapter = require('./adapters/stt/assemblyaiAdapter');
          break;
        default:
          throw new Error(`Unknown STT provider: ${this.provider}`);
      }

      this.logger.info(`✓ ${this.provider} STT initialized`);
    } catch (error) {
      this.logger.error(`Failed to initialize ${this.provider}:`, error.message);
      throw error;
    }
  }

  /**
   * Transcribe audio to text
   *
   * @param {Buffer} audioBuffer - PCM audio buffer
   * @param {Object} options - Optional parameters (e.g., sampleRate)
   * @returns {Promise<Object>} - { text, confidence, isFinal }
   */
  async transcribe(audioBuffer, options = {}) {
    try {
      // Pass sample rate to adapter for proper conversion
      const result = await this.adapter.transcribe(audioBuffer, {
        ...this.config,
        sampleRate: options.sampleRate || 8000, // Default Exotel rate
        ...options
      });

      if (result.text) {
        this.logger.debug(`Transcribed: "${result.text}"`);
      }

      return result;
    } catch (error) {
      this.logger.error('Transcription error:', error.message);
      throw error;
    }
  }

  /**
   * Start streaming transcription session
   *
   * @param {Function} onTranscript - Callback for interim/final transcripts
   * @param {Function} onError - Error callback
   * @returns {Object} - Stream session with send() and end() methods
   */
  createStream(onTranscript, onError) {
    try {
      return this.adapter.createStream(this.config, onTranscript, onError);
    } catch (error) {
      this.logger.error('Stream creation error:', error.message);
      throw error;
    }
  }

  /**
   * Get provider info
   */
  getInfo() {
    return {
      provider: this.provider,
      config: this.config
    };
  }
}

module.exports = STTService;

