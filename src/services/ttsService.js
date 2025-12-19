/**
 * Text-to-Speech Service
 * Unified interface for multiple TTS providers
 */

const Logger = require('../utils/logger');
const aiConfig = require('../../config/ai-services.config');

class TTSService {
  constructor(provider = null) {
    this.provider = provider || aiConfig.tts.provider;
    this.config = aiConfig.tts[this.provider];
    this.logger = new Logger(`TTS-${this.provider.toUpperCase()}`);
    this.adapter = null;

    this.initialize();
  }

  /**
   * Initialize TTS adapter based on provider
   */
  initialize() {
    this.logger.info(`Initializing ${this.provider} TTS service...`);

    try {
      switch (this.provider) {
        case 'elevenlabs':
          this.adapter = require('./adapters/tts/elevenlabsAdapter');
          break;
        case 'openai':
          this.adapter = require('./adapters/tts/openaiTTSAdapter');
          break;
        case 'google':
          this.adapter = require('./adapters/tts/googleTTSAdapter');
          break;
        case 'azure':
          this.adapter = require('./adapters/tts/azureTTSAdapter');
          break;
        case 'playht':
          this.adapter = require('./adapters/tts/playhtAdapter');
          break;
        default:
          throw new Error(`Unknown TTS provider: ${this.provider}`);
      }

      this.logger.info(`✓ ${this.provider} TTS initialized`);
    } catch (error) {
      this.logger.error(`Failed to initialize ${this.provider}:`, error.message);
      throw error;
    }
  }

  /**
   * Convert text to speech
   *
   * @param {string} text - Text to convert
   * @param {Object} options - Optional parameters (e.g., targetSampleRate)
   * @returns {Promise<Buffer>} - PCM audio buffer at target sample rate
   */
  async synthesize(text, options = {}) {
    try {
      const startTime = Date.now();

      const audioBuffer = await this.adapter.synthesize(text, {
        ...this.config,
        targetSampleRate: options.targetSampleRate || 8000, // Default Exotel rate
        ...options
      });

      const duration = Date.now() - startTime;
      this.logger.debug(`Synthesized "${text.substring(0, 30)}..." in ${duration}ms`);

      return audioBuffer;
    } catch (error) {
      this.logger.error('Synthesis error:', error.message);
      throw error;
    }
  }

  /**
   * Stream text-to-speech
   *
   * @param {string} text - Text to convert
   * @param {Object} options - Optional parameters
   * @returns {AsyncGenerator<Buffer>} - Stream of audio chunks
   */
  async *stream(text, options = {}) {
    try {
      const stream = this.adapter.stream(text, {
        ...this.config,
        ...options
      });

      for await (const chunk of stream) {
        yield chunk;
      }
    } catch (error) {
      this.logger.error('Stream synthesis error:', error.message);
      throw error;
    }
  }

  /**
   * Get available voices
   */
  async getVoices() {
    try {
      if (this.adapter.getVoices) {
        return await this.adapter.getVoices(this.config);
      }
      return [];
    } catch (error) {
      this.logger.error('Get voices error:', error.message);
      return [];
    }
  }

  /**
   * Get provider info
   */
  getInfo() {
    return {
      provider: this.provider,
      voice: this.config.voiceId || this.config.voiceName || this.config.voice,
      config: this.config
    };
  }
}

module.exports = TTSService;

