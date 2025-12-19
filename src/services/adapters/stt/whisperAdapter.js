/**
 * OpenAI Whisper STT Adapter
 * Install: npm install openai
 */

const Logger = require('../../../utils/logger');
const AudioResampler = require('../../../utils/audioResampler');
const logger = new Logger('WHISPER');

let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.warn('OpenAI SDK not installed. Install with: npm install openai');
}

class WhisperAdapter {
  /**
   * Transcribe audio buffer
   * Whisper needs at least 0.1 seconds of audio (16kHz = 1600 samples minimum)
   */
  static async transcribe(audioBuffer, config) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    try {
      // Whisper expects 16kHz audio
      const resampledBuffer = AudioResampler.to16kHz(audioBuffer, config.sampleRate || 8000);

      // Check minimum duration (0.1 seconds)
      const duration = AudioResampler.getDuration(resampledBuffer, 16000);
      if (duration < 100) {
        logger.debug(`Audio too short (${duration}ms), skipping...`);
        return { text: '', confidence: 0, isFinal: false };
      }

      const openai = new OpenAI({
        apiKey: config.apiKey
      });

      // Convert PCM to WAV format (Whisper needs WAV/MP3/etc)
      const wavBuffer = this.pcmToWav(resampledBuffer, 16000);

      // Create file object
      const file = new File([wavBuffer], 'audio.wav', { type: 'audio/wav' });

      // Transcribe
      const transcription = await openai.audio.transcriptions.create({
        file: file,
        model: config.model || 'whisper-1',
        language: config.language || 'en',
        response_format: 'verbose_json'
      });

      return {
        text: transcription.text,
        confidence: 1.0, // Whisper doesn't provide confidence
        isFinal: true
      };
    } catch (error) {
      logger.error('Whisper transcription error:', error.message);
      throw error;
    }
  }

  /**
   * Create streaming session
   * Note: Whisper doesn't support true streaming, so we batch audio
   */
  static createStream(config, onTranscript, onError) {
    if (!OpenAI) {
      throw new Error('OpenAI SDK not installed');
    }

    let audioBuffer = Buffer.alloc(0);
    const minBufferSize = 32000; // ~1 second at 16kHz (32000 bytes = 16000 samples)
    const maxBufferSize = 320000; // ~10 seconds

    return {
      send: async (chunk) => {
        try {
          // Accumulate audio
          audioBuffer = Buffer.concat([audioBuffer, chunk]);

          // Process when we have enough audio
          if (audioBuffer.length >= minBufferSize) {
            const result = await this.transcribe(audioBuffer, config);

            if (result.text) {
              // Send interim result
              onTranscript({
                text: result.text,
                isFinal: false,
                confidence: 1.0
              });
            }

            // Clear buffer if too large
            if (audioBuffer.length >= maxBufferSize) {
              audioBuffer = Buffer.alloc(0);

              // Send final result
              if (result.text) {
                onTranscript({
                  text: result.text,
                  isFinal: true,
                  confidence: 1.0
                });
              }
            }
          }
        } catch (error) {
          logger.error('Stream processing error:', error.message);
          onError(error);
        }
      },

      end: async () => {
        try {
          // Process any remaining audio
          if (audioBuffer.length > 0) {
            const result = await this.transcribe(audioBuffer, config);
            if (result.text) {
              onTranscript({
                text: result.text,
                isFinal: true,
                confidence: 1.0
              });
            }
          }
          audioBuffer = Buffer.alloc(0);
        } catch (error) {
          logger.error('Stream end error:', error.message);
          onError(error);
        }
      }
    };
  }

  /**
   * Convert PCM to WAV format
   * Whisper API requires WAV, MP3, etc. (not raw PCM)
   */
  static pcmToWav(pcmBuffer, sampleRate) {
    const numChannels = 1; // Mono
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = pcmBuffer.length;
    const headerSize = 44;
    const fileSize = headerSize + dataSize;

    const wavBuffer = Buffer.alloc(fileSize);
    let offset = 0;

    // RIFF header
    wavBuffer.write('RIFF', offset); offset += 4;
    wavBuffer.writeUInt32LE(fileSize - 8, offset); offset += 4;
    wavBuffer.write('WAVE', offset); offset += 4;

    // fmt chunk
    wavBuffer.write('fmt ', offset); offset += 4;
    wavBuffer.writeUInt32LE(16, offset); offset += 4; // Subchunk size
    wavBuffer.writeUInt16LE(1, offset); offset += 2; // Audio format (1 = PCM)
    wavBuffer.writeUInt16LE(numChannels, offset); offset += 2;
    wavBuffer.writeUInt32LE(sampleRate, offset); offset += 4;
    wavBuffer.writeUInt32LE(byteRate, offset); offset += 4;
    wavBuffer.writeUInt16LE(blockAlign, offset); offset += 2;
    wavBuffer.writeUInt16LE(bitsPerSample, offset); offset += 2;

    // data chunk
    wavBuffer.write('data', offset); offset += 4;
    wavBuffer.writeUInt32LE(dataSize, offset); offset += 4;
    pcmBuffer.copy(wavBuffer, offset);

    return wavBuffer;
  }
}

module.exports = WhisperAdapter;

