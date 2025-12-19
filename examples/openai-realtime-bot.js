/**
 * OpenAI Realtime Speech-to-Speech Bot
 *
 * TRUE end-to-end speech-to-speech using OpenAI's Realtime API
 * Audio in → GPT-4o → Audio out (no text intermediate!)
 *
 * Expected latency: ~300-500ms (vs 3-5s with pipeline)
 *
 * Reference: https://platform.openai.com/docs/guides/realtime
 */

const ExotelWSSServer = require('../src/core/server');
const Logger = require('../src/core/utils/logger');
const AudioResampler = require('../src/core/utils/audioResampler');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('../src/core/utils/botUtils');
const WebSocket = require('ws');

const logger = new Logger('OPENAI-REALTIME');

// Audio format constants
const AUDIO_FORMAT = {
  EXOTEL_SAMPLE_RATE: 8000,     // Exotel uses 8kHz
  OPENAI_SAMPLE_RATE: 24000,    // OpenAI Realtime uses 24kHz
  OPENAI_FORMAT: 'pcm16'        // 16-bit PCM
};

class OpenAIRealtimeBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    this.apiKey = process.env.OPENAI_API_KEY;
    this.cachedGreeting = null;  // Pre-cached greeting audio

    if (!this.apiKey) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ OPENAI_API_KEY not configured!');
      logger.error('');
      logger.error('Add to your .env file:');
      logger.error('  OPENAI_API_KEY=sk-proj-your-key-here');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    logger.info('═══════════════════════════════════════════════════════');
    logger.info('🚀 OpenAI Realtime Speech-to-Speech Bot');
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('   Model: gpt-4o-realtime-preview');
    logger.info('   Latency: ~300-500ms (true S2S)');
    logger.info('   Audio: 8kHz ↔ 24kHz conversion');
    logger.info('═══════════════════════════════════════════════════════');

    // Pre-cache greeting for instant playback
    this.cacheGreeting().catch(err => {
      logger.warn('Could not pre-cache greeting:', err.message);
    });
  }

  /**
   * Pre-cache greeting audio using OpenAI TTS
   * Called once at startup for instant greeting on call connect
   */
  async cacheGreeting() {
    const OpenAI = require('openai').default;
    const openai = new OpenAI({ apiKey: this.apiKey });

    logger.info('⏳ Pre-caching greeting audio...');
    const startTime = Date.now();

    const response = await openai.audio.speech.create({
      model: 'tts-1',
      voice: 'alloy',
      input: 'Hi! How can I help you today?',
      response_format: 'pcm',
      speed: 1.0
    });

    // TTS returns 24kHz, resample to 8kHz for Exotel
    const audioData = Buffer.from(await response.arrayBuffer());
    this.cachedGreeting = AudioResampler.resample(audioData, 24000, 8000);

    logger.info(`✅ Greeting cached in ${Date.now() - startTime}ms (${this.cachedGreeting.length} bytes)`);
  }

  /**
   * Initialize session for a new call
   */
  initializeSession(streamId) {
    const state = new SessionState(streamId);

    return {
      streamId,
      sampleRate: 8000,
      openaiWs: null,
      connected: false,
      state,  // Use SessionState for proper turn-taking
      lastActivity: Date.now(),
      sender: null,
      // ═══════════════════════════════════════════════════════
      // AUDIO SMOOTHING BUFFER
      // Accumulate audio deltas and send in smooth chunks
      // ═══════════════════════════════════════════════════════
      audioOutputBuffer: Buffer.alloc(0),
      audioFlushInterval: null,
      FLUSH_INTERVAL_MS: 50,   // Flush every 50ms for smoother audio
      MIN_BUFFER_SIZE: 3200    // 200ms minimum (Exotel requirement)
    };
  }

  /**
   * Connect to OpenAI Realtime API
   */
  connectToOpenAI(session, sender) {
    return new Promise((resolve, reject) => {
      const wsUrl = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17';

      logger.info('🔌 Connecting to OpenAI Realtime API...');

      const ws = new WebSocket(wsUrl, {
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'OpenAI-Beta': 'realtime=v1'
        }
      });

      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error('OpenAI connection timeout'));
      }, 10000);

      ws.on('open', () => {
        clearTimeout(timeout);
        logger.info('✅ Connected to OpenAI Realtime API');
        session.openaiWs = ws;
        session.connected = true;

        // Configure the session
        const sessionConfig = {
          type: 'session.update',
          session: {
            modalities: ['audio', 'text'],
            instructions: `You are a helpful voice assistant. Keep responses very brief (1-2 sentences max). 
Be conversational and friendly. Respond quickly and naturally.`,
            voice: 'alloy',
            input_audio_format: 'pcm16',
            output_audio_format: 'pcm16',
            input_audio_transcription: {
              model: 'whisper-1'
            },
            turn_detection: {
              type: 'server_vad',
              threshold: 0.6,           // Higher threshold = less sensitive
              prefix_padding_ms: 200,   // Less padding = faster response
              silence_duration_ms: 400  // Faster turn detection
            }
          }
        };

        ws.send(JSON.stringify(sessionConfig));
        logger.info('→ Session configured');

        resolve();
      });

      ws.on('message', (data) => {
        this.handleOpenAIMessage(session, sender, data);
      });

      ws.on('error', (error) => {
        clearTimeout(timeout);
        logger.error('❌ OpenAI WebSocket error:', error.message);
        reject(error);
      });

      ws.on('close', (code, reason) => {
        clearTimeout(timeout);
        logger.info(`OpenAI WebSocket closed: ${code}`);
        session.connected = false;
      });
    });
  }

  /**
   * Handle messages from OpenAI Realtime API
   */
  handleOpenAIMessage(session, sender, data) {
    try {
      const message = JSON.parse(data.toString());

      switch (message.type) {
        case 'session.created':
          logger.info('✓ OpenAI session created');
          break;

        case 'session.updated':
          logger.info('✓ OpenAI session configured');
          // Send initial greeting
          this.sendGreeting(session, sender);
          break;

        case 'input_audio_buffer.speech_started':
          logger.info('🎤 User started speaking');
          session.state.isUserSpeaking = true;
          // Barge-in: stop bot audio
          if (session.state.isBotSpeaking) {
            // Clear audio buffer
            session.audioOutputBuffer = Buffer.alloc(0);
            BargeInHandler.handle(session.state, sender, session.openaiWs);
          }
          break;

        case 'input_audio_buffer.speech_stopped':
          logger.info('🎤 User stopped speaking');
          session.state.isUserSpeaking = false;
          break;

        case 'conversation.item.input_audio_transcription.completed':
          logger.info(`📝 User: "${message.transcript}"`);
          break;

        case 'response.audio.delta':
          // Receive audio chunk from OpenAI
          this.handleAudioDelta(session, sender, message);
          break;

        case 'response.audio.done':
          // Flush remaining audio buffer (sends padded final chunk)
          this.flushAudioBuffer(session, sender);

          logger.info('🔊 Response audio complete');
          session.state.stopSpeaking();
          sender.sendMark(`response-complete-${Date.now()}`);
          break;

        case 'response.audio_transcript.delta':
          // Partial transcript of bot response
          break;

        case 'response.audio_transcript.done':
          logger.info(`🤖 Bot: "${message.transcript}"`);
          break;

        case 'response.done':
          logger.debug('Response complete');
          break;

        case 'error':
          logger.error('OpenAI error:', message.error);
          break;

        default:
          logger.debug(`OpenAI event: ${message.type}`);
      }

    } catch (error) {
      logger.error('Error parsing OpenAI message:', error.message);
    }
  }

  /**
   * Handle audio delta from OpenAI
   * Buffers audio for smooth playback (prevents choppy voice)
   */
  handleAudioDelta(session, sender, message) {
    if (!message.delta) return;

    try {
      // Decode base64 audio (24kHz PCM16)
      const audioData = Buffer.from(message.delta, 'base64');

      // Resample from 24kHz to 8kHz for Exotel
      const resampledAudio = AudioResampler.resample(
        audioData,
        AUDIO_FORMAT.OPENAI_SAMPLE_RATE,
        AUDIO_FORMAT.EXOTEL_SAMPLE_RATE
      );

      // Mark bot as speaking
      session.state.startSpeaking();

      // ═══════════════════════════════════════════════════════
      // AUDIO BUFFERING: Accumulate until we have minimum chunk
      // ═══════════════════════════════════════════════════════
      session.audioOutputBuffer = Buffer.concat([session.audioOutputBuffer, resampledAudio]);

      // Send complete 3200-byte chunks immediately (don't wait)
      while (session.audioOutputBuffer.length >= session.MIN_BUFFER_SIZE) {
        const chunk = session.audioOutputBuffer.slice(0, session.MIN_BUFFER_SIZE);
        session.audioOutputBuffer = session.audioOutputBuffer.slice(session.MIN_BUFFER_SIZE);
        sender.sendMedia(chunk);
      }

    } catch (error) {
      logger.error('Error processing audio delta:', error.message);
    }
  }

  /**
   * Flush remaining audio buffer to Exotel
   */
  flushAudioBuffer(session, sender) {
    if (session.audioOutputBuffer.length === 0) return;

    // Pad remaining audio to minimum chunk size
    if (session.audioOutputBuffer.length > 0) {
      const paddedChunk = Buffer.alloc(session.MIN_BUFFER_SIZE, 0);
      session.audioOutputBuffer.copy(paddedChunk);
      sender.sendMedia(paddedChunk);
    }

    // Clear buffer
    session.audioOutputBuffer = Buffer.alloc(0);
  }

  /**
   * Send greeting via OpenAI (used as fallback if cached greeting not available)
   */
  sendGreeting(session, sender) {
    if (!session.openaiWs || !session.connected) return;

    // Skip if we already sent cached greeting
    if (this.cachedGreeting) {
      logger.debug('Skipping OpenAI greeting (cached already sent)');
      return;
    }

    logger.info('🎤 Sending greeting via OpenAI...');

    // Create a text response for greeting
    const createResponse = {
      type: 'response.create',
      response: {
        modalities: ['audio', 'text'],
        instructions: 'Say a brief greeting like "Hi! How can I help you today?"'
      }
    };

    session.openaiWs.send(JSON.stringify(createResponse));
  }

  /**
   * Forward audio to OpenAI (with buffering for efficiency)
   */
  forwardAudioToOpenAI(session, audioBuffer) {
    if (!session.openaiWs || !session.connected) return;

    // Skip if bot is speaking (reduce noise during playback)
    if (session.state.isBotSpeaking) return;

    try {
      // Resample from 8kHz to 24kHz for OpenAI
      const resampledAudio = AudioResampler.resample(
        audioBuffer,
        AUDIO_FORMAT.EXOTEL_SAMPLE_RATE,
        AUDIO_FORMAT.OPENAI_SAMPLE_RATE
      );

      // Send as base64
      const audioMessage = {
        type: 'input_audio_buffer.append',
        audio: resampledAudio.toString('base64')
      };

      session.openaiWs.send(JSON.stringify(audioMessage));

    } catch (error) {
      logger.error('Error forwarding audio:', error.message);
    }
  }

  /**
   * Get message callbacks for Exotel events
   */
  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    this.sessions.set(streamId, session);

    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('🎙️  OpenAI Realtime Session Started');
    logger.info(`   Stream: ${streamId.substring(0, 8)}`);
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    return {
      onStart: async (streamInfo) => {
        const callStartTime = Date.now();
        logger.info(`📞 Call started: ${streamInfo.call_sid}`);
        logger.info(`   From: ${streamInfo.from} → To: ${streamInfo.to}`);

        session.sampleRate = streamInfo.sample_rate || 8000;
        session.sender = sender;

        // ═══════════════════════════════════════════════════════
        // INSTANT GREETING: Send cached audio immediately
        // This happens BEFORE connecting to OpenAI (~0ms latency)
        // ═══════════════════════════════════════════════════════
        if (this.cachedGreeting) {
          const greetingStartTime = Date.now();
          session.state.startSpeaking();

          // Send in 3200-byte chunks
          const CHUNK_SIZE = 3200;
          for (let i = 0; i < this.cachedGreeting.length; i += CHUNK_SIZE) {
            const chunk = this.cachedGreeting.slice(i, Math.min(i + CHUNK_SIZE, this.cachedGreeting.length));
            if (chunk.length < CHUNK_SIZE) {
              const padded = Buffer.alloc(CHUNK_SIZE, 0);
              chunk.copy(padded);
              sender.sendMedia(padded);
            } else {
              sender.sendMedia(chunk);
            }
          }
          sender.sendMark('greeting-complete');

          logger.info(`⚡ INSTANT greeting sent in ${Date.now() - greetingStartTime}ms`);
        } else {
          // Fallback: send early media if no cached greeting
          AudioUtils.sendEarlyMedia(sender);
        }

        // ═══════════════════════════════════════════════════════
        // Connect to OpenAI in background while greeting plays
        // ═══════════════════════════════════════════════════════
        this.connectToOpenAI(session, sender)
          .then(() => {
            logger.info(`✅ OpenAI ready (${Date.now() - callStartTime}ms from call start)`);
            session.state.stopSpeaking();
          })
          .catch(error => {
            logger.error('Failed to connect to OpenAI:', error.message);
            session.state.stopSpeaking();
          });
      },

      onMedia: (mediaData) => {
        if (!session.connected) return;

        session.lastActivity = Date.now();

        // Forward audio to OpenAI
        this.forwardAudioToOpenAI(session, mediaData.audioBuffer);
      },

      onMark: (markData) => {
        logger.debug(`Mark received: ${markData.name}`);
      },

      onStop: (stopData) => {
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        logger.info(`✓ Session ended: ${stopData.reason}`);
        logger.info(`   Duration: ${(stopData.duration / 1000).toFixed(2)}s`);
        logger.info(`   Turns: ${session.state.turnCount}`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        // Close OpenAI connection
        if (session.openaiWs) {
          session.openaiWs.close();
        }

        this.sessions.delete(streamId);
      }
    };
  }
}

// Start the bot
const bot = new OpenAIRealtimeBot();
bot.start();

