/**
 * Gemini 2.0 Flash Live API Bridge Bot
 *
 * Bridges Exotel WebSocket with Google Gemini Live API
 * True native audio input/output - no separate STT/TTS needed!
 *
 * Audio Format Handling:
 * - Exotel sends: 16-bit PCM 8kHz mono
 * - Gemini expects: 16-bit PCM 16kHz mono
 * - Gemini outputs: 16-bit PCM 24kHz mono
 * - Bridge resamples in both directions
 *
 * Reference: https://ai.google.dev/gemini-api/docs/live
 */

const ExotelWSSServer = require('../src/server');
const Logger = require('../src/utils/logger');
const AudioResampler = require('../src/utils/audioResampler');
const WebSocket = require('ws');

const logger = new Logger('GEMINI-LIVE');

// Audio format constants
const AUDIO_FORMAT = {
  EXOTEL_SAMPLE_RATE: 8000,       // Exotel uses 8kHz
  GEMINI_INPUT_RATE: 16000,       // Gemini expects 16kHz input
  GEMINI_OUTPUT_RATE: 24000       // Gemini outputs 24kHz
};

// Gemini Live API endpoint
const GEMINI_LIVE_URL = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent';

class GeminiLiveBridgeBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    this.apiKey = process.env.GEMINI_API_KEY;

    if (!this.apiKey) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ GEMINI_API_KEY not configured!');
      logger.error('');
      logger.error('Add to your .env file:');
      logger.error('  GEMINI_API_KEY=your_api_key_here');
      logger.error('');
      logger.error('Get your API key from: https://aistudio.google.com/apikey');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    logger.info(`✓ Gemini API Key configured (${this.apiKey.substring(0, 8)}...)`);
  }

  /**
   * Initialize session for a new call
   */
  initializeSession(streamId) {
    return {
      streamId,
      geminiWs: null,
      connected: false,
      setupComplete: false,
      lastActivity: Date.now(),
      // State tracking
      agentSpeaking: false,
      interrupted: false,
      audioChunks: 0,
      responseChunks: 0,
      // Audio buffer for accumulating before sending
      audioBuffer: Buffer.alloc(0),
      MIN_CHUNK_SIZE: 640,  // 20ms at 16kHz, 16-bit
      // Custom parameters
      customParams: {}
    };
  }

  /**
   * Connect to Gemini Live API
   */
  connectToGemini(session) {
    return new Promise((resolve, reject) => {
      // Gemini Live WebSocket URL with API key
      const wsUrl = `${GEMINI_LIVE_URL}?key=${this.apiKey}`;

      logger.info('🔌 Connecting to Gemini Live API...');
      logger.info(`   Input format: 16-bit PCM ${AUDIO_FORMAT.GEMINI_INPUT_RATE}Hz`);
      logger.info(`   Output format: 16-bit PCM ${AUDIO_FORMAT.GEMINI_OUTPUT_RATE}Hz`);

      const ws = new WebSocket(wsUrl);

      ws.on('open', () => {
        logger.info('✅ Connected to Gemini Live API');
        session.connected = true;

        // Send setup message
        const setupMessage = {
          setup: {
            model: 'models/gemini-2.0-flash-exp',
            generationConfig: {
              responseModalities: ['AUDIO'],
              speechConfig: {
                voiceConfig: {
                  prebuiltVoiceConfig: {
                    voiceName: 'Aoede'  // Options: Aoede, Charon, Fenrir, Kore, Puck
                  }
                }
              }
            },
            systemInstruction: {
              parts: [{
                text: `You are a helpful voice assistant for Exotel. 
                Keep responses concise (1-2 sentences).
                Be friendly, natural, and conversational.
                You are speaking over the phone so be clear and articulate.`
              }]
            }
          }
        };

        ws.send(JSON.stringify(setupMessage));
        logger.debug('→ Sent setup message');
      });

      ws.on('message', (data) => {
        this.handleGeminiMessage(session, data);

        // Resolve once setup is complete
        if (session.setupComplete && !session.resolved) {
          session.resolved = true;
          resolve();
        }
      });

      ws.on('error', (error) => {
        logger.error('❌ Gemini WebSocket error:', error.message);
        reject(error);
      });

      ws.on('close', (code, reason) => {
        logger.info(`🔌 Gemini WebSocket closed (code: ${code})`);
        session.connected = false;
      });

      session.geminiWs = ws;

      // Timeout for setup
      setTimeout(() => {
        if (!session.setupComplete) {
          reject(new Error('Gemini setup timeout'));
        }
      }, 10000);
    });
  }

  /**
   * Handle messages from Gemini Live API
   */
  handleGeminiMessage(session, data) {
    try {
      const message = JSON.parse(data.toString());

      // Setup complete
      if (message.setupComplete) {
        logger.info('✅ Gemini setup complete');
        session.setupComplete = true;
        return;
      }

      // Server content (audio/text response)
      if (message.serverContent) {
        const content = message.serverContent;

        // Check if turn is complete
        if (content.turnComplete) {
          logger.debug('🔊 Gemini turn complete');
          session.agentSpeaking = false;
          this.flushAudioBuffer(session);
          this.sendMarkToExotel(session, 'gemini_response_complete');
          return;
        }

        // Check if interrupted
        if (content.interrupted) {
          logger.info('⚠️ Gemini detected interruption');
          session.interrupted = true;
          session.agentSpeaking = false;
          session.audioBuffer = Buffer.alloc(0);
          this.sendClearToExotel(session);
          return;
        }

        // Process model turn parts
        if (content.modelTurn && content.modelTurn.parts) {
          for (const part of content.modelTurn.parts) {
            // Audio response
            if (part.inlineData && part.inlineData.mimeType === 'audio/pcm') {
              session.agentSpeaking = true;
              session.interrupted = false;
              this.forwardAudioToExotel(session, part.inlineData.data);
            }

            // Text response (for logging)
            if (part.text) {
              logger.info(`🤖 Gemini: "${part.text}"`);
            }
          }
        }
      }

      // Tool calls (if any)
      if (message.toolCall) {
        logger.info(`🔧 Tool call: ${message.toolCall.functionCalls?.[0]?.name || 'unknown'}`);
      }

    } catch (error) {
      logger.error('Error handling Gemini message:', error.message);
    }
  }

  /**
   * Send audio to Gemini Live API
   */
  sendAudioToGemini(session, audioBuffer) {
    if (!session.connected || !session.geminiWs || !session.setupComplete) {
      return;
    }

    try {
      // Resample from 8kHz to 16kHz for Gemini
      const resampledBuffer = AudioResampler.resample(
        audioBuffer,
        AUDIO_FORMAT.EXOTEL_SAMPLE_RATE,
        AUDIO_FORMAT.GEMINI_INPUT_RATE
      );

      // Convert to base64
      const base64Audio = resampledBuffer.toString('base64');

      // Send realtime input
      const message = {
        realtimeInput: {
          mediaChunks: [{
            mimeType: 'audio/pcm',
            data: base64Audio
          }]
        }
      };

      session.geminiWs.send(JSON.stringify(message));

      session.audioChunks = (session.audioChunks || 0) + 1;
      if (session.audioChunks % 50 === 0) {
        logger.debug(`→ Sent ${session.audioChunks} audio chunks to Gemini`);
      }

    } catch (error) {
      logger.error('Error sending audio to Gemini:', error.message);
    }
  }

  /**
   * Forward audio from Gemini to Exotel
   * Resamples from 24kHz (Gemini) to 8kHz (Exotel)
   */
  forwardAudioToExotel(session, base64Audio) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) {
      return;
    }

    try {
      if (session.interrupted) {
        return;
      }

      // Decode base64
      const geminiBuffer = Buffer.from(base64Audio, 'base64');

      // Resample from 24kHz to 8kHz for Exotel
      const exotelBuffer = AudioResampler.resample(
        geminiBuffer,
        AUDIO_FORMAT.GEMINI_OUTPUT_RATE,
        AUDIO_FORMAT.EXOTEL_SAMPLE_RATE
      );

      // Accumulate in buffer
      session.audioBuffer = Buffer.concat([session.audioBuffer, exotelBuffer]);

      // Send in chunks
      const CHUNK_SIZE = 640;  // 20ms chunks for low latency

      while (session.audioBuffer.length >= CHUNK_SIZE) {
        if (session.interrupted) {
          session.audioBuffer = Buffer.alloc(0);
          break;
        }

        const chunk = session.audioBuffer.slice(0, CHUNK_SIZE);
        session.audioBuffer = session.audioBuffer.slice(CHUNK_SIZE);

        sender.sendMedia(chunk, null, true);  // Skip validation
        session.responseChunks++;
      }

    } catch (error) {
      logger.error('Error forwarding audio to Exotel:', error.message);
    }
  }

  /**
   * Flush remaining audio buffer
   */
  flushAudioBuffer(session) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender || session.interrupted) {
      session.audioBuffer = Buffer.alloc(0);
      return;
    }

    if (session.audioBuffer.length >= 320) {
      const paddedLength = Math.ceil(session.audioBuffer.length / 320) * 320;
      const paddedBuffer = Buffer.alloc(paddedLength);
      session.audioBuffer.copy(paddedBuffer);
      sender.sendMedia(paddedBuffer, null, true);
    }

    session.audioBuffer = Buffer.alloc(0);
  }

  /**
   * Send CLEAR to Exotel
   */
  sendClearToExotel(session) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) return;

    try {
      sender.sendClear();
      logger.info('🧹 Sent CLEAR to Exotel');
    } catch (error) {
      logger.error('Error sending clear:', error.message);
    }
  }

  /**
   * Send MARK to Exotel
   */
  sendMarkToExotel(session, markName) {
    const sender = this.connections.get(session.streamId)?.sender;
    if (!sender) return;

    try {
      sender.sendMark(markName);
    } catch (error) {
      logger.error('Error sending mark:', error.message);
    }
  }

  /**
   * Get message callbacks for Exotel events
   */
  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    this.sessions.set(streamId, session);

    return {
      onStart: async (streamInfo) => {
        logger.info('═══════════════════════════════════════════════════════');
        logger.info('📞 Call started');
        logger.info(`   Stream ID: ${streamId.substring(0, 16)}...`);
        logger.info(`   Call SID: ${streamInfo.call_sid || 'N/A'}`);
        logger.info(`   From: ${streamInfo.from || 'N/A'}`);
        logger.info(`   Sample Rate: ${streamInfo.media_format?.sample_rate || 8000}Hz`);

        if (streamInfo.custom_parameters) {
          session.customParams = streamInfo.custom_parameters;
          logger.info(`   Custom Params: ${JSON.stringify(session.customParams)}`);
        }
        logger.info('═══════════════════════════════════════════════════════');

        try {
          await this.connectToGemini(session);
          logger.info('🎙️ Gemini Live bridge ready! Start speaking...');
        } catch (error) {
          logger.error('Failed to connect to Gemini:', error.message);
        }
      },

      onMedia: (mediaData) => {
        if (!session.connected || !session.setupComplete) {
          return;
        }

        session.lastActivity = Date.now();

        // Forward audio to Gemini
        this.sendAudioToGemini(session, mediaData.audioBuffer);
      },

      onDTMF: (dtmfData) => {
        logger.info(`📱 DTMF: ${dtmfData.digit}`);

        if (dtmfData.digit === '#') {
          logger.info('📞 Call ending (# pressed)');
          if (session.geminiWs) {
            session.geminiWs.close();
          }
        }
      },

      onMark: (markData) => {
        logger.debug(`✓ Mark received: ${markData.name}`);
      },

      onStop: (stopData) => {
        logger.info('═══════════════════════════════════════════════════════');
        logger.info('📞 Call ended');
        logger.info(`   Audio chunks sent: ${session.audioChunks}`);
        logger.info(`   Response chunks: ${session.responseChunks}`);
        logger.info('═══════════════════════════════════════════════════════');

        if (session.geminiWs) {
          session.geminiWs.close();
        }

        this.sessions.delete(streamId);
      }
    };
  }
}

// Start server
const bot = new GeminiLiveBridgeBot();
const PORT = process.env.PORT || 5001;

bot.start(PORT);

logger.info('');
logger.info('═══════════════════════════════════════════════════════');
logger.info('🎙️ Gemini 2.0 Flash Live Bridge Bot Ready!');
logger.info('═══════════════════════════════════════════════════════');
logger.info('');
logger.info('📞 How it works:');
logger.info('   ┌──────────┐      ┌─────────────┐      ┌────────────┐');
logger.info('   │  Exotel  │ ←──→ │ This Bridge │ ←──→ │  Gemini    │');
logger.info('   │  (Call)  │      │   Server    │      │  Live API  │');
logger.info('   └──────────┘      └─────────────┘      └────────────┘');
logger.info('      8kHz             Resamples           16kHz/24kHz');
logger.info('');
logger.info('🔊 Audio Format Conversion:');
logger.info('   Exotel → Bridge: 16-bit PCM 8kHz');
logger.info('   Bridge → Gemini: 16-bit PCM 16kHz');
logger.info('   Gemini → Bridge: 16-bit PCM 24kHz');
logger.info('   Bridge → Exotel: 16-bit PCM 8kHz');
logger.info('');
logger.info('⚡ Features:');
logger.info('   • Native audio input AND output');
logger.info('   • No separate STT/TTS needed');
logger.info('   • Real-time bidirectional streaming');
logger.info('   • Ultra-low latency');
logger.info('');
logger.info('═══════════════════════════════════════════════════════');
logger.info('Press Ctrl+C to stop');
logger.info('═══════════════════════════════════════════════════════');

module.exports = GeminiLiveBridgeBot;

