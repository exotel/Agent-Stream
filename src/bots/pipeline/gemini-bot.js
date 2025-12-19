/**
 * Gemini Speech-to-Speech AI Voice Bot
 *
 * Hybrid approach: Gemini 2.0 Flash for AI + OpenAI for TTS
 * Fast, optimized, natural conversations
 *
 * Uses: Google Gemini 2.5 Flash + OpenAI TTS
 */

const ExotelWSSServer = require('../src/server');
const AudioResampler = require('../src/utils/audioResampler');
const Logger = require('../src/utils/logger');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('../src/utils/botUtils');
const fs = require('fs');
const path = require('path');

const logger = new Logger('GEMINI-BOT');

// Google Generative AI SDK
let GoogleGenerativeAI;
try {
  const { GoogleGenerativeAI: SDK } = require('@google/generative-ai');
  GoogleGenerativeAI = SDK;
} catch (error) {
  logger.error('Google Generative AI SDK not installed. Install with: npm install @google/generative-ai');
  process.exit(1);
}

// OpenAI for TTS (Gemini doesn't have TTS yet)
let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.error('OpenAI SDK not installed. Install with: npm install openai');
  process.exit(1);
}

class GeminiSpeechBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    this.cachedGreeting = null; // Pre-cached greeting audio for instant playback

    // Initialize Gemini
    this.genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

    // Initialize OpenAI for TTS
    this.openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });

    if (!process.env.GEMINI_API_KEY) {
      logger.error('GEMINI_API_KEY not configured in .env');
      process.exit(1);
    }

    if (!process.env.OPENAI_API_KEY) {
      logger.error('OPENAI_API_KEY not configured in .env (needed for TTS)');
      process.exit(1);
    }

    logger.info('✅ Gemini Speech-to-Speech Bot initialized');
    logger.info('   AI: Gemini 2.5 Flash');
    logger.info('   Voice: OpenAI TTS');

    // Pre-cache greeting on startup for instant playback
    this.preCacheGreeting();
  }

  /**
   * Pre-cache greeting audio on startup to eliminate TTS latency on first call
   */
  async preCacheGreeting() {
    try {
      logger.info('⏳ Pre-caching greeting audio...');
      const startTime = Date.now();

      const response = await this.openai.audio.speech.create({
        model: 'tts-1',
        voice: 'alloy',
        input: "Hi! I'm powered by Gemini. How can I help you today?",
        response_format: 'pcm',
        speed: 1.1
      });

      const audioData = Buffer.from(await response.arrayBuffer());
      // Pre-resample to 8kHz for immediate use
      this.cachedGreeting = AudioResampler.resample(audioData, 24000, 8000);

      const duration = Date.now() - startTime;
      logger.info(`✅ Greeting cached in ${duration}ms (${this.cachedGreeting.length} bytes)`);
    } catch (error) {
      logger.error('Failed to pre-cache greeting:', error.message);
    }
  }

  initializeSession(streamId) {
    const sampleRate = this.connections.get(streamId)?.sampleRate || 8000;

    return {
      streamId,
      sampleRate,
      audioBuffer: [],
      isProcessing: false,
      conversationHistory: [],
      silenceCounter: 0,
      // ═══════════════════════════════════════════════════════
      // LATENCY OPTIMIZED PARAMETERS
      // ═══════════════════════════════════════════════════════
      silenceThreshold: 8,    // 160ms of silence (was 15 = 300ms)
      minAudioChunks: 25,     // 0.5s minimum speech (was 80 = 2s)
      processingCooldown: 800, // 800ms cooldown (was 1500ms)
      // ═══════════════════════════════════════════════════════
      lastActivity: Date.now(),
      chunkCount: 0,
      processingInterval: null,
      lastProcessedTime: Date.now(),
      sender: null,
      // ═══════════════════════════════════════════════════════
      // BARGE-IN / INTERRUPTION HANDLING
      // ═══════════════════════════════════════════════════════
      isBotSpeaking: false,   // Track if bot is currently playing audio
      interrupted: false,      // Track if user interrupted
      pendingMarks: new Map(), // Track sent marks and their timestamps
      audioStartTime: 0       // When audio started playing
    };
  }

  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    session.sender = sender;
    this.sessions.set(streamId, session);

    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('🤖 Gemini Speech-to-Speech Bot Session Started');
    logger.info(`   Stream: ${streamId.substring(0, 8)}`);
    logger.info('   AI: Gemini 2.5 Flash');
    logger.info('   Voice: OpenAI TTS (Fast)');
    logger.info(`   Sample Rate: ${session.sampleRate} Hz`);
    logger.info('   ⚡ Latency Optimized:');
    logger.info(`      Min speech: ${session.minAudioChunks * 40}ms (${session.minAudioChunks} chunks)`);
    logger.info(`      Silence detect: ${session.silenceThreshold * 40}ms`);
    logger.info(`      Cooldown: ${session.processingCooldown}ms`);
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // Start periodic processing (backup - every 1 second for faster response)
    session.processingInterval = setInterval(() => {
      const currentSession = this.sessions.get(streamId);
      if (!currentSession) return;

      if (currentSession.audioBuffer.length >= currentSession.minAudioChunks &&
          !currentSession.isProcessing &&
          (Date.now() - currentSession.lastProcessedTime) > currentSession.processingCooldown) {

        const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
        logger.info(`⏰ Interval trigger: ${currentSession.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s)`);

        currentSession.lastProcessedTime = Date.now();
        this.processGeminiSpeech(streamId, currentSession.sender).catch(err => {
          logger.error('Interval processing error:', err.message);
        });
      }
    }, 1000); // Reduced from 2000ms to 1000ms for faster response

    return {
      onStart: async (streamInfo) => {
        logger.info(`📞 Call started: ${streamInfo.call_sid}`);
        logger.info(`   From: ${streamInfo.from} → To: ${streamInfo.to}`);

        // Send early media
        this.sendEarlyMedia(sender, session.sampleRate);

        // Send greeting immediately
        setImmediate(async () => {
          try {
            await this.sendGreeting(streamId, sender);
            logger.info('🎤 Greeting sent - ready for conversation');
          } catch (error) {
            logger.error('Error sending greeting:', error.message);
          }
        });
      },

      onMedia: (mediaData) => {
        // Get fresh session reference (critical for session persistence)
        const currentSession = this.sessions.get(streamId);
        if (!currentSession) return;

        currentSession.lastActivity = Date.now();
        currentSession.chunkCount++;

        try {
          const audioBuffer = mediaData.audioBuffer;
          const audioLevel = this.calculateAudioLevel(audioBuffer);
          const isSilent = audioLevel < 300;

          // ═══════════════════════════════════════════════════════
          // BARGE-IN: Clear audio when user speaks during bot response
          // ═══════════════════════════════════════════════════════
          if (!isSilent && currentSession.isBotSpeaking) {
            logger.info('⚡ BARGE-IN: User interrupted! Clearing audio.');
            currentSession.sender.sendClear();
            currentSession.isBotSpeaking = false;
            currentSession.interrupted = true;
          }

          if (isSilent) {
            currentSession.silenceCounter++;
          } else {
            currentSession.silenceCounter = 0;
            currentSession.audioBuffer.push(audioBuffer);
          }

          if (currentSession.chunkCount % 50 === 0) {
            const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
            logger.debug(`📦 Buffer: ${currentSession.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s), silence: ${currentSession.silenceCounter}`);
          }

          const hasEnoughAudio = currentSession.audioBuffer.length >= currentSession.minAudioChunks;
          const detectedPause = currentSession.silenceCounter >= currentSession.silenceThreshold;
          const notRecentlyProcessed = (Date.now() - currentSession.lastProcessedTime) > currentSession.processingCooldown;

          if (hasEnoughAudio && detectedPause && !currentSession.isProcessing && notRecentlyProcessed) {
            const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
            logger.info(`🎤 Silence detected! Processing ${currentSession.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s)...`);

            currentSession.lastProcessedTime = Date.now();
            currentSession.silenceCounter = 0;

            this.processGeminiSpeech(streamId, currentSession.sender).catch(err => {
              logger.error('Processing error:', err.message);
            });
          }
        } catch (error) {
          logger.error('Error processing media:', error.message);
          if (currentSession) currentSession.isProcessing = false;
        }
      },

      // ═══════════════════════════════════════════════════════
      // MARK EVENT: Track audio playback completion
      // ═══════════════════════════════════════════════════════
      onMark: (markData) => {
        const currentSession = this.sessions.get(streamId);
        if (!currentSession) return;

        const markName = markData.name;
        logger.info(`🏷️  Mark received: ${markName}`);

        // Check if this is a response completion mark
        if (markName.startsWith('response-complete-') || markName.startsWith('greeting-complete-')) {
          currentSession.isBotSpeaking = false;

          // Calculate actual playback latency
          if (currentSession.pendingMarks.has(markName)) {
            const sentTime = currentSession.pendingMarks.get(markName);
            const playbackLatency = Date.now() - sentTime;
            logger.info(`⏱️  Playback latency: ${playbackLatency}ms`);
            currentSession.pendingMarks.delete(markName);
          }
        }
      },

      onDTMF: (dtmfData) => {
        logger.info(`🔢 DTMF: ${dtmfData.digit}`);
        if (dtmfData.digit === '#') {
          logger.info('User ending call...');
          ws.close(1000, 'User ended call');
        }
      },

      onStop: async (stopData) => {
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        logger.info('✓ Gemini session ended');
        logger.info(`  Duration: ${(stopData.duration / 1000).toFixed(2)}s`);
        logger.info(`  Turns: ${session.conversationHistory.length / 2}`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        if (session.processingInterval) {
          clearInterval(session.processingInterval);
        }
        this.sessions.delete(streamId);
      }
    };
  }

  calculateAudioLevel(audioBuffer) {
    let sum = 0;
    for (let i = 0; i < audioBuffer.length; i += 2) {
      const sample = audioBuffer.readInt16LE(i);
      sum += Math.abs(sample);
    }
    return sum / (audioBuffer.length / 2);
  }

  sendEarlyMedia(sender, sampleRate) {
    // Send minimum 3200 bytes (200ms at 8kHz) to meet Exotel requirements
    const CHUNK_SIZE = 3200;
    const silence = Buffer.alloc(CHUNK_SIZE, 0);
    sender.sendMedia(silence);
    logger.debug('→ Early media sent (200ms silence)');
  }

  async sendGreeting(streamId, sender) {
    const session = this.sessions.get(streamId);
    if (!session) return;

    const startTime = Date.now();

    try {
      let resampledAudio;

      // Use pre-cached greeting for instant playback (< 50ms vs 2-3s)
      if (this.cachedGreeting) {
        resampledAudio = this.cachedGreeting;
        logger.info('⚡ Using cached greeting (instant playback)');
      } else {
        // Fallback: generate on-demand if cache not ready
        logger.info('⏳ Generating greeting (cache not ready)...');
        const response = await this.openai.audio.speech.create({
          model: 'tts-1',
          voice: 'alloy',
          input: "Hi! I'm powered by Gemini. How can I help you today?",
          response_format: 'pcm',
          speed: 1.1
        });

        const audioData = Buffer.from(await response.arrayBuffer());
        resampledAudio = AudioResampler.resample(audioData, 24000, session.sampleRate);
      }

      sender.sendClear();

      // Mark bot as speaking for barge-in detection
      session.isBotSpeaking = true;
      session.interrupted = false;
      session.audioStartTime = Date.now();

      // Send in 3200-byte chunks (200ms at 8kHz) - Exotel minimum
      const CHUNK_SIZE = 3200;
      let chunksSent = 0;
      for (let i = 0; i < resampledAudio.length; i += CHUNK_SIZE) {
        const chunk = resampledAudio.slice(i, Math.min(i + CHUNK_SIZE, resampledAudio.length));
        // Pad final chunk if needed
        if (chunk.length < CHUNK_SIZE && chunk.length > 0) {
          const paddedChunk = Buffer.alloc(CHUNK_SIZE, 0);
          chunk.copy(paddedChunk);
          sender.sendMedia(paddedChunk);
        } else {
          sender.sendMedia(chunk);
        }
        chunksSent++;
      }

      // Send mark to track when greeting finishes playing
      const markName = `greeting-complete-${Date.now()}`;
      session.pendingMarks.set(markName, Date.now());
      sender.sendMark(markName);

      const latency = Date.now() - startTime;
      logger.info(`→ Greeting sent: ${chunksSent} chunks, ${resampledAudio.length} bytes in ${latency}ms`);
    } catch (error) {
      logger.error('Error sending greeting:', error.message);
    }
  }

  async processGeminiSpeech(streamId, sender) {
    const session = this.sessions.get(streamId);
    if (!session || session.audioBuffer.length === 0) return;
    if (session.isProcessing) return;

    session.isProcessing = true;
    const processingStartTime = Date.now();

    try {
      const combinedAudio = Buffer.concat(session.audioBuffer);
      const audioChunks = session.audioBuffer.length;
      session.audioBuffer = [];

      const audioSeconds = combinedAudio.length / (session.sampleRate * 2);
      logger.info(`🎤 Processing ${audioChunks} chunks (${audioSeconds.toFixed(1)}s)...`);

      // Convert to WAV and base64 for Gemini
      const geminiStart = Date.now();
      const wavBuffer = this.createWavBuffer(combinedAudio, session.sampleRate);
      const base64Audio = wavBuffer.toString('base64');

      // Send to Gemini
      const model = this.genAI.getGenerativeModel({
        model: 'gemini-2.5-flash',
        systemInstruction: 'You are a helpful voice assistant. Keep responses very concise (1-2 sentences max). Be friendly and conversational.'
      });

      // Build chat history
      const chatHistory = session.conversationHistory.slice(-10);

      const result = await model.generateContent([
        {
          inlineData: {
            mimeType: 'audio/wav',
            data: base64Audio
          }
        },
        'Listen to this audio and respond naturally and concisely to what the user said.'
      ]);

      const response = await result.response;
      const aiResponse = response.text();
      const geminiTime = Date.now() - geminiStart;

      if (!aiResponse || aiResponse.trim().length < 2) {
        logger.warn('⚠️  Empty Gemini response');
        session.isProcessing = false;
        return;
      }

      logger.info(`🤖 Gemini: "${aiResponse}" (${geminiTime}ms)`);

      // Store in history
      session.conversationHistory.push({ role: 'user', audio: true });
      session.conversationHistory.push({ role: 'model', text: aiResponse });
      if (session.conversationHistory.length > 20) {
        session.conversationHistory = session.conversationHistory.slice(-20);
      }

      // Generate speech
      const ttsStart = Date.now();
      const ttsResponse = await this.openai.audio.speech.create({
        model: 'tts-1',
        voice: 'alloy',
        input: aiResponse,
        response_format: 'pcm',
        speed: 1.1
      });

      const responseAudio = Buffer.from(await ttsResponse.arrayBuffer());
      const ttsTime = Date.now() - ttsStart;

      // ═══════════════════════════════════════════════════════
      // SEND AUDIO TO EXOTEL
      // ═══════════════════════════════════════════════════════
      const resampledAudio = AudioResampler.resample(responseAudio, 24000, session.sampleRate);

      // Clear any pending audio FIRST (enables immediate playback)
      sender.sendClear();

      // Mark bot as speaking for barge-in detection
      session.isBotSpeaking = true;
      session.interrupted = false;
      session.audioStartTime = Date.now();

      // Send in 3200-byte chunks (200ms at 8kHz) - Exotel minimum
      const CHUNK_SIZE = 3200;
      let chunksSent = 0;
      for (let i = 0; i < resampledAudio.length; i += CHUNK_SIZE) {
        // Check if interrupted mid-send
        if (session.interrupted) {
          logger.info(`⏹️  Audio send stopped (user interrupted after ${chunksSent} chunks)`);
          break;
        }

        const chunk = resampledAudio.slice(i, Math.min(i + CHUNK_SIZE, resampledAudio.length));
        // Pad final chunk if needed
        if (chunk.length < CHUNK_SIZE && chunk.length > 0) {
          const paddedChunk = Buffer.alloc(CHUNK_SIZE, 0);
          chunk.copy(paddedChunk);
          sender.sendMedia(paddedChunk);
        } else {
          sender.sendMedia(chunk);
        }
        chunksSent++;
      }

      // Send mark to track when audio finishes playing
      const markName = `response-complete-${Date.now()}`;
      session.pendingMarks.set(markName, Date.now());
      sender.sendMark(markName);

      const totalTime = Date.now() - processingStartTime;
      const audioSecs = resampledAudio.length / (session.sampleRate * 2);
      logger.info(`🔊 Response sent: ${chunksSent} chunks, ${audioSecs.toFixed(1)}s audio`);
      logger.info(`✅ Complete: Gemini ${geminiTime}ms + TTS ${ttsTime}ms = ${totalTime}ms`);

    } catch (error) {
      logger.error('Gemini processing error:', error.message);
      try {
        const errorResponse = await this.openai.audio.speech.create({
          model: 'tts-1',
          voice: 'alloy',
          input: 'Sorry, I had trouble with that. Could you repeat?',
          response_format: 'pcm'
        });
        const errorAudio = Buffer.from(await errorResponse.arrayBuffer());
        const resampled = AudioResampler.resample(errorAudio, 24000, session.sampleRate);
        sender.sendMedia(resampled);
      } catch (e) {
        logger.error('Failed to send error message:', e.message);
      }
    } finally {
      session.isProcessing = false;
    }
  }

  createWavBuffer(pcmBuffer, sampleRate) {
    const wavHeader = Buffer.alloc(44);
    const dataSize = pcmBuffer.length;
    const fileSize = dataSize + 36;

    wavHeader.write('RIFF', 0);
    wavHeader.writeUInt32LE(fileSize, 4);
    wavHeader.write('WAVE', 8);
    wavHeader.write('fmt ', 12);
    wavHeader.writeUInt32LE(16, 16);
    wavHeader.writeUInt16LE(1, 20);
    wavHeader.writeUInt16LE(1, 22);
    wavHeader.writeUInt32LE(sampleRate, 24);
    wavHeader.writeUInt32LE(sampleRate * 2, 28);
    wavHeader.writeUInt16LE(2, 32);
    wavHeader.writeUInt16LE(16, 34);
    wavHeader.write('data', 36);
    wavHeader.writeUInt32LE(dataSize, 40);

    return Buffer.concat([wavHeader, pcmBuffer]);
  }
}

const port = process.env.PORT || 5001;
const bot = new GeminiSpeechBot();

bot.start(port).then(() => {
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('🤖 Gemini Speech-to-Speech Bot Ready!');
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('Powered by:');
  logger.info('  • Google Gemini 2.5 Flash');
  logger.info('  • OpenAI TTS (Voice)');
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('Features:');
  logger.info('  • Immediate greeting (1-2s)');
  logger.info('  • Silence detection (300ms)');
  logger.info('  • Fast responses (3-5s)');
  logger.info('  • Natural conversation');
  logger.info('═══════════════════════════════════════════════════════');
}).catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});

module.exports = GeminiSpeechBot;
