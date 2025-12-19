/**
 * ElevenLabs TTS Adapter
 * Install: npm install elevenlabs
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('ELEVENLABS');

let ElevenLabsClient;
try {
  ElevenLabsClient = require('elevenlabs');
} catch (error) {
  logger.warn('ElevenLabs SDK not installed. Install with: npm install elevenlabs');
}

class ElevenLabsAdapter {
  /**
   * Synthesize text to speech
   */
  static async synthesize(text, config) {
    if (!ElevenLabsClient) {
      throw new Error('ElevenLabs SDK not installed');
    }

    try {
      const elevenlabs = new ElevenLabsClient({
        apiKey: config.apiKey
      });

      const audio = await elevenlabs.generate({
        voice: config.voiceId,
        text: text,
        model_id: config.model,
        voice_settings: {
          stability: config.stability,
          similarity_boost: config.similarityBoost
        }
      });

      // Convert stream to buffer
      const chunks = [];
      for await (const chunk of audio) {
        chunks.push(chunk);
      }

      return Buffer.concat(chunks);
    } catch (error) {
      logger.error('ElevenLabs synthesis error:', error.message);
      throw error;
    }
  }

  /**
   * Stream synthesis
   */
  static async *stream(text, config) {
    if (!ElevenLabsClient) {
      throw new Error('ElevenLabs SDK not installed');
    }

    try {
      const elevenlabs = new ElevenLabsClient({
        apiKey: config.apiKey
      });

      const audio = await elevenlabs.generate({
        voice: config.voiceId,
        text: text,
        model_id: config.model,
        voice_settings: {
          stability: config.stability,
          similarity_boost: config.similarityBoost
        },
        stream: true
      });

      for await (const chunk of audio) {
        yield chunk;
      }
    } catch (error) {
      logger.error('ElevenLabs stream error:', error.message);
      throw error;
    }
  }

  /**
   * Get available voices
   */
  static async getVoices(config) {
    if (!ElevenLabsClient) {
      throw new Error('ElevenLabs SDK not installed');
    }

    try {
      const elevenlabs = new ElevenLabsClient({
        apiKey: config.apiKey
      });

      const voices = await elevenlabs.voices.getAll();
      return voices.voices.map(v => ({
        id: v.voice_id,
        name: v.name,
        description: v.description
      }));
    } catch (error) {
      logger.error('ElevenLabs get voices error:', error.message);
      return [];
    }
  }
}

module.exports = ElevenLabsAdapter;

