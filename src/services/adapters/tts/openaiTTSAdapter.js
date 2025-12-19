/**
 * OpenAI TTS Adapter
 * Install: npm install openai
 */

const Logger = require('../../../utils/logger');
const AudioResampler = require('../../../utils/audioResampler');
const logger = new Logger('OPENAI-TTS');

let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.warn('OpenAI SDK not installed. Install with: npm install openai');
}

class OpenAITTSAdapter {
  /**
   * Synthesize text to speech
   * OpenAI TTS outputs various formats - we convert to PCM
   */
  static async synthesize(text, config) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    try {
      const openai = new OpenAI({
        apiKey: config.apiKey
      });

      // Generate speech
      const mp3Response = await openai.audio.speech.create({
        model: config.model || 'tts-1', // or 'tts-1-hd'
        voice: config.voice || 'alloy', // alloy, echo, fable, onyx, nova, shimmer
        input: text,
        response_format: 'pcm', // Get PCM directly
        speed: config.speed || 1.0
      });

      // Convert response to buffer
      const arrayBuffer = await mp3Response.arrayBuffer();
      let pcmBuffer = Buffer.from(arrayBuffer);

      // OpenAI TTS outputs 24kHz PCM by default
      // Resample to target rate (usually 8kHz for Exotel)
      const targetRate = config.targetSampleRate || 8000;
      if (targetRate !== 24000) {
        pcmBuffer = AudioResampler.resample(pcmBuffer, 24000, targetRate);
      }

      return pcmBuffer;
    } catch (error) {
      logger.error('OpenAI TTS error:', error.message);
      throw error;
    }
  }

  /**
   * Stream synthesis
   * OpenAI TTS doesn't support true streaming yet, but we can chunk the output
   */
  static async *stream(text, config) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    try {
      // Generate complete audio
      const audioBuffer = await this.synthesize(text, config);

      // Chunk size (e.g., 3200 bytes = 100ms at 8kHz)
      const chunkSize = config.chunkSize || 3200;

      // Yield chunks
      for (let i = 0; i < audioBuffer.length; i += chunkSize) {
        const chunk = audioBuffer.slice(i, Math.min(i + chunkSize, audioBuffer.length));
        yield chunk;
      }
    } catch (error) {
      logger.error('OpenAI TTS stream error:', error.message);
      throw error;
    }
  }

  /**
   * Get available voices
   */
  static async getVoices(config) {
    // OpenAI TTS has fixed voices
    return [
      { id: 'alloy', name: 'Alloy', description: 'Neutral, balanced voice' },
      { id: 'echo', name: 'Echo', description: 'Male, clear voice' },
      { id: 'fable', name: 'Fable', description: 'Male, expressive voice' },
      { id: 'onyx', name: 'Onyx', description: 'Male, deep voice' },
      { id: 'nova', name: 'Nova', description: 'Female, friendly voice' },
      { id: 'shimmer', name: 'Shimmer', description: 'Female, warm voice' }
    ];
  }
}

module.exports = OpenAITTSAdapter;

