/**
 * Deepgram STT Adapter
 * Install: npm install @deepgram/sdk
 */

const Logger = require('../../../utils/logger');
const logger = new Logger('DEEPGRAM');

let DeepgramClient;
try {
  const { createClient } = require('@deepgram/sdk');
  DeepgramClient = createClient;
} catch (error) {
  logger.warn('Deepgram SDK not installed. Install with: npm install @deepgram/sdk');
}

class DeepgramAdapter {
  /**
   * Transcribe audio buffer
   */
  static async transcribe(audioBuffer, config) {
    if (!DeepgramClient) {
      throw new Error('Deepgram SDK not installed');
    }

    try {
      const deepgram = DeepgramClient(config.apiKey);

      const { result } = await deepgram.listen.prerecorded.transcribeFile(
        audioBuffer,
        {
          model: config.model,
          language: config.language,
          punctuate: true,
          diarize: false
        }
      );

      const transcript = result.results.channels[0].alternatives[0].transcript;
      const confidence = result.results.channels[0].alternatives[0].confidence;

      return {
        text: transcript,
        confidence: confidence,
        isFinal: true
      };
    } catch (error) {
      logger.error('Deepgram transcription error:', error.message);
      throw error;
    }
  }

  /**
   * Create streaming session
   */
  static createStream(config, onTranscript, onError) {
    if (!DeepgramClient) {
      throw new Error('Deepgram SDK not installed');
    }

    try {
      const deepgram = DeepgramClient(config.apiKey);

      const connection = deepgram.listen.live({
        model: config.model,
        language: config.language,
        punctuate: true,
        interim_results: config.interimResults,
        encoding: config.encoding,
        sample_rate: config.sampleRate
      });

      connection.on('Results', (data) => {
        const transcript = data.channel.alternatives[0].transcript;
        const isFinal = data.is_final;
        const confidence = data.channel.alternatives[0].confidence;

        if (transcript) {
          onTranscript({
            text: transcript,
            isFinal: isFinal,
            confidence: confidence
          });
        }
      });

      connection.on('error', (error) => {
        logger.error('Deepgram stream error:', error);
        onError(error);
      });

      return {
        send: (audioBuffer) => {
          connection.send(audioBuffer);
        },
        end: () => {
          connection.finish();
        }
      };
    } catch (error) {
      logger.error('Deepgram stream creation error:', error.message);
      throw error;
    }
  }
}

module.exports = DeepgramAdapter;

