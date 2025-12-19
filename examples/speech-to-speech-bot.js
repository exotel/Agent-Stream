/**
 * Speech-to-Speech AI Voice Bot
 *
 * Direct speech-to-speech using OpenAI's audio capabilities
 * Lower latency, more natural conversations
 *
 * Uses: OpenAI GPT-4o with audio input/output
 */

const ExotelWSSServer = require('../src/core/server');
const AudioProcessor = require('../src/core/audio/audioProcessor');
const AudioResampler = require('../src/core/utils/audioResampler');
const Logger = require('../src/core/utils/logger');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('../src/core/utils/botUtils');
const fs = require('fs');
const path = require('path');

const logger = new Logger('S2S-BOT');

// OpenAI SDK
let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.error('OpenAI SDK not installed. Install with: npm install openai');
  process.exit(1);
}

class SpeechToSpeechBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    this.openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });

    if (!process.env.OPENAI_API_KEY) {
      logger.error('OPENAI_API_KEY not configured in .env');
      process.exit(1);
    }
  }

  /**
   * Initialize session for a new call
   */
  initializeSession(streamId) {
    const sampleRate = this.connections.get(streamId)?.sampleRate || 8000;

    return {
      streamId,
      sampleRate,
      audioProcessor: new AudioProcessor(streamId, { sampleRate }),
      audioBuffer: [],
      isProcessing: false,
      conversationHistory: [],
      silenceCounter: 0,
      silenceThreshold: 15, // ~300ms of silence (15 chunks × 20ms)
      minAudioChunks: 50, // ~1 second minimum (reduced for faster response)
      lastActivity: Date.now(),
      tempAudioFile: path.join(__dirname, '..', 'logs', `temp_audio_${streamId}.wav`),
      chunkCount: 0,
      processingInterval: null,
      lastProcessedTime: Date.now(),
      sender: null,
      // ═══════════════════════════════════════════════════════
      // TURN-TAKING STATE
      // ═══════════════════════════════════════════════════════
      isBotSpeaking: false  // Prevents processing while bot is talking
    };
  }

  /**
   * Get message callbacks
   */
  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    session.sender = sender; // Store sender for interval access
    this.sessions.set(streamId, session);

    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('🎙️  Speech-to-Speech Bot Session Started');
    logger.info(`   Stream: ${streamId.substring(0, 8)}`);
    logger.info('   Mode: Direct Speech-to-Speech');
    logger.info('   Model: GPT-4o with Audio');
    logger.info(`   Sample Rate: ${session.sampleRate} Hz`);
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // ═══════════════════════════════════════════════════════
    // DISABLED: Interval processing causes race conditions
    // Silence detection in onMedia handles all processing now
    // ═══════════════════════════════════════════════════════
    session.processingInterval = null;

    return {
      onStart: async (streamInfo) => {
        logger.info(`📞 Call started: ${streamInfo.call_sid}`);
        logger.info(`   From: ${streamInfo.from} → To: ${streamInfo.to}`);

        // Send early media for pipeline warmup
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

      onMedia: async (mediaData) => {
        session.lastActivity = Date.now();
        session.chunkCount++;

        try {
          // ═══════════════════════════════════════════════════════
          // BARGE-IN: If user speaks while bot is talking, stop bot
          // ═══════════════════════════════════════════════════════
          const audioLevel = this.calculateAudioLevel(mediaData.audioBuffer);
          const isSilent = audioLevel < 300;

          if (!isSilent && session.isBotSpeaking) {
            logger.info('⚡ BARGE-IN: User interrupted bot!');
            sender.sendClear();
            session.isBotSpeaking = false;
            session.audioBuffer = []; // Clear old buffer
            return; // Don't process this chunk
          }

          // ═══════════════════════════════════════════════════════
          // SKIP: Don't buffer audio while bot is speaking or processing
          // ═══════════════════════════════════════════════════════
          if (session.isBotSpeaking || session.isProcessing) {
            return; // Skip - bot is busy
          }

          // Process incoming audio
          const cleanAudio = await session.audioProcessor.processIncomingAudio(
            mediaData.audioBuffer
          );

          if (isSilent) {
            session.silenceCounter++;
          } else {
            session.silenceCounter = 0;
            session.audioBuffer.push(cleanAudio);
          }

          // Log progress every 50 chunks
          if (session.chunkCount % 50 === 0) {
            const audioSeconds = (session.audioBuffer.length * 320) / (session.sampleRate * 2);
            logger.debug(`📦 Buffer: ${session.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s)`);
          }

          // ═══════════════════════════════════════════════════════
          // TRIGGER: Process when enough audio + silence detected
          // ═══════════════════════════════════════════════════════
          const hasEnoughAudio = session.audioBuffer.length >= session.minAudioChunks;
          const detectedPause = session.silenceCounter >= session.silenceThreshold;
          const notRecentlyProcessed = (Date.now() - session.lastProcessedTime) > 1500;

          if (hasEnoughAudio && detectedPause && !session.isProcessing && notRecentlyProcessed) {
            // ═══════════════════════════════════════════════════════
            // CRITICAL: Set flags SYNCHRONOUSLY before async processing
            // ═══════════════════════════════════════════════════════
            session.isProcessing = true;  // Lock immediately
            session.lastProcessedTime = Date.now();
            session.silenceCounter = 0;

            // Copy buffer and clear it immediately (prevent re-processing)
            const audioToProcess = [...session.audioBuffer];
            session.audioBuffer = [];

            const audioSeconds = (audioToProcess.length * 320) / (session.sampleRate * 2);
            logger.info(`🎤 Processing ${audioToProcess.length} chunks (${audioSeconds.toFixed(1)}s)...`);

            // Process asynchronously
            this.processSpeechToSpeech(streamId, sender, audioToProcess).catch(err => {
              logger.error('Processing error:', err.message);
              session.isProcessing = false;
            });
          }

        } catch (error) {
          logger.error('Error processing media:', error.message);
          session.isProcessing = false;
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
        logger.info('✓ Speech-to-Speech session ended');
        logger.info(`  Reason: ${stopData.reason}`);
        logger.info(`  Duration: ${(stopData.duration / 1000).toFixed(2)}s`);
        logger.info(`  Turns: ${session.conversationHistory.length}`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        // Clear interval
        if (session.processingInterval) {
          clearInterval(session.processingInterval);
        }

        // Cleanup
        await session.audioProcessor.destroy();

        // Remove temp files
        if (fs.existsSync(session.tempAudioFile)) {
          fs.unlinkSync(session.tempAudioFile);
        }

        this.sessions.delete(streamId);
      }
    };
  }

  /**
   * Send greeting message
   */
  async sendGreeting(streamId, sender) {
    const session = this.sessions.get(streamId);
    if (!session) return;

    try {
      logger.info('🎤 Sending greeting...');

      const greeting = "Hi! I'm your assistant. How can I help?";

      // Use TTS to generate greeting (optimized speed)
      const response = await this.openai.audio.speech.create({
        model: 'tts-1', // Fast model
        voice: 'alloy',
        input: greeting,
        response_format: 'pcm',
        speed: 1.1 // 10% faster for snappier greeting
      });

      // Convert response to buffer
      const audioData = Buffer.from(await response.arrayBuffer());

      // Resample to target rate
      const resampledAudio = AudioResampler.resample(
        audioData,
        24000, // OpenAI TTS outputs at 24kHz
        session.sampleRate
      );

      // Clean outgoing audio
      const cleanAudio = await session.audioProcessor.processOutgoingAudio(resampledAudio);

      // Clear any pending audio before sending
      sender.sendClear();

      // Mark bot as speaking (prevents processing incoming audio)
      session.isBotSpeaking = true;

      // Send in 3200-byte chunks (200ms at 8kHz) - Exotel minimum
      const CHUNK_SIZE = 3200;
      let chunksSent = 0;
      for (let i = 0; i < cleanAudio.length; i += CHUNK_SIZE) {
        const chunk = cleanAudio.slice(i, Math.min(i + CHUNK_SIZE, cleanAudio.length));
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

      // Send mark event
      sender.sendMark(`greeting-complete-${Date.now()}`);

      // Bot finished speaking
      session.isBotSpeaking = false;

      logger.info(`✓ Greeting sent: ${chunksSent} chunks, ${cleanAudio.length} bytes`);

    } catch (error) {
      logger.error('Error sending greeting:', error.message);
    }
  }

  /**
   * Process speech-to-speech interaction
   * @param {string} streamId - Stream ID
   * @param {Object} sender - Message sender
   * @param {Array} audioChunks - Audio chunks to process (passed to avoid race conditions)
   */
  async processSpeechToSpeech(streamId, sender, audioChunks) {
    const session = this.sessions.get(streamId);
    if (!session || !audioChunks || audioChunks.length === 0) {
      session.isProcessing = false;
      return;
    }

    try {
      const startTime = Date.now();

      // Combine all buffered audio (from passed parameter, not session)
      const fullAudio = Buffer.concat(audioChunks);

      logger.info(`🎙️  Processing speech (${fullAudio.length} bytes)...`);

      // ═══════════════════════════════════════════════════════
      // Step 1: Speech-to-Text (to get transcript)
      // ═══════════════════════════════════════════════════════
      const transcript = await this.transcribeAudio(fullAudio, session.sampleRate);

      if (!transcript || transcript.trim().length === 0) {
        logger.warn('Empty transcript, skipping...');
        return;
      }

      logger.info(`📝 User said: "${transcript}"`);

      // ═══════════════════════════════════════════════════════
      // Step 2: Get AI response (text)
      // ═══════════════════════════════════════════════════════
      const aiResponse = await this.getAIResponse(transcript, session);

      logger.info(`🤖 AI responds: "${aiResponse}"`);

      // ═══════════════════════════════════════════════════════
      // Step 3: Text-to-Speech (generate audio response)
      // ═══════════════════════════════════════════════════════
      const responseAudio = await this.synthesizeSpeech(aiResponse);

      // ═══════════════════════════════════════════════════════
      // Step 4: Resample and send to caller
      // ═══════════════════════════════════════════════════════
      const resampledAudio = AudioResampler.resample(
        responseAudio,
        24000, // OpenAI TTS output rate
        session.sampleRate
      );

      // Clean outgoing audio
      const cleanAudio = await session.audioProcessor.processOutgoingAudio(resampledAudio);

      // Clear pending audio before sending new response
      sender.sendClear();

      // ═══════════════════════════════════════════════════════
      // Mark bot as speaking (prevents processing incoming audio)
      // ═══════════════════════════════════════════════════════
      session.isBotSpeaking = true;

      // Send in 3200-byte chunks (200ms at 8kHz) - Exotel minimum
      const CHUNK_SIZE = 3200;
      let chunksSent = 0;
      for (let i = 0; i < cleanAudio.length; i += CHUNK_SIZE) {
        const chunk = cleanAudio.slice(i, Math.min(i + CHUNK_SIZE, cleanAudio.length));
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

      // Send mark event
      sender.sendMark(`response-complete-${Date.now()}`);

      const totalTime = Date.now() - startTime;
      const audioSeconds = cleanAudio.length / (session.sampleRate * 2);
      logger.info(`🔊 Response sent: ${chunksSent} chunks, ${audioSeconds.toFixed(1)}s audio, ${totalTime}ms latency`);

      // Store in conversation history
      session.conversationHistory.push({
        user: transcript,
        assistant: aiResponse,
        timestamp: new Date().toISOString(),
        latency: totalTime
      });

      // ═══════════════════════════════════════════════════════
      // Bot finished speaking - ready for next input
      // ═══════════════════════════════════════════════════════
      session.isBotSpeaking = false;
      session.isProcessing = false;

    } catch (error) {
      logger.error('Error in speech-to-speech processing:', error.message);
      session.isProcessing = false;
      session.isBotSpeaking = false;

      // Send error message to caller
      try {
        const errorAudio = await this.synthesizeSpeech(
          'Sorry, could you repeat that?'
        );
        const resampledError = AudioResampler.resample(errorAudio, 24000, session.sampleRate);
        sender.sendMedia(resampledError);
      } catch (e) {
        logger.error('Failed to send error message:', e.message);
      }
    }
  }

  /**
   * Send early media (silence) to establish audio path
   */
  sendEarlyMedia(sender, sampleRate) {
    const CHUNK_SIZE = 3200; // 200ms at 8kHz
    const silence = Buffer.alloc(CHUNK_SIZE, 0);
    sender.sendMedia(silence);
    logger.debug('→ Early media sent (200ms silence)');
  }

  /**
   * Calculate audio level for silence detection
   */
  calculateAudioLevel(audioBuffer) {
    if (!audioBuffer || audioBuffer.length < 2) return 0;
    let sum = 0;
    for (let i = 0; i < audioBuffer.length - 1; i += 2) {
      const sample = audioBuffer.readInt16LE(i);
      sum += Math.abs(sample);
    }
    return sum / (audioBuffer.length / 2);
  }

  /**
   * Transcribe audio using OpenAI Whisper
   */
  async transcribeAudio(audioBuffer, sampleRate) {
    try {
      // Convert PCM to WAV format
      const wavBuffer = this.createWavBuffer(audioBuffer, sampleRate);

      // Create temporary file
      const tempFile = path.join(__dirname, '..', 'logs', `temp_${Date.now()}.wav`);
      fs.writeFileSync(tempFile, wavBuffer);

      // Transcribe using Whisper
      const transcription = await this.openai.audio.transcriptions.create({
        file: fs.createReadStream(tempFile),
        model: 'whisper-1',
        language: 'en'
      });

      // Cleanup temp file
      fs.unlinkSync(tempFile);

      return transcription.text;

    } catch (error) {
      logger.error('Transcription error:', error.message);
      throw error;
    }
  }

  /**
   * Get AI response using GPT-4
   */
  async getAIResponse(userMessage, session) {
    try {
      // Build conversation context
      const messages = [
        {
          role: 'system',
          content: 'You are a helpful voice assistant. Keep responses concise (1-2 sentences), natural, and conversational. Speak in a friendly, helpful tone.'
        }
      ];

      // Add conversation history (last 5 turns)
      const recentHistory = session.conversationHistory.slice(-5);
      recentHistory.forEach(turn => {
        messages.push({ role: 'user', content: turn.user });
        messages.push({ role: 'assistant', content: turn.assistant });
      });

      // Add current message
      messages.push({ role: 'user', content: userMessage });

      // Get response from GPT-4
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4-turbo-preview',
        messages: messages,
        max_tokens: 150,
        temperature: 0.7
      });

      return completion.choices[0].message.content;

    } catch (error) {
      logger.error('LLM error:', error.message);
      return "I'm having trouble processing that right now. Could you try again?";
    }
  }

  /**
   * Synthesize speech using OpenAI TTS
   */
  async synthesizeSpeech(text) {
    try {
      const response = await this.openai.audio.speech.create({
        model: 'tts-1', // Fast model for low latency
        voice: 'alloy',
        input: text,
        response_format: 'pcm',
        speed: 1.1 // 10% faster for snappier responses
      });

      const audioData = Buffer.from(await response.arrayBuffer());
      return audioData;

    } catch (error) {
      logger.error('TTS error:', error.message);
      throw error;
    }
  }

  /**
   * Check if audio chunk is silence
   */
  isSilence(audioBuffer, threshold = 800) {
    let sum = 0;
    let count = 0;

    // Sample every 2 bytes (16-bit audio)
    for (let i = 0; i < audioBuffer.length; i += 2) {
      const sample = Math.abs(audioBuffer.readInt16LE(i));
      sum += sample;
      count++;
    }

    const average = count > 0 ? sum / count : 0;
    const isSilent = average < threshold;

    // Log occasionally for debugging
    if (Math.random() < 0.01) { // 1% of the time
      logger.debug(`Silence check: avg=${average.toFixed(0)}, threshold=${threshold}, silent=${isSilent}`);
    }

    return isSilent;
  }

  /**
   * Create WAV buffer from PCM
   */
  createWavBuffer(pcmBuffer, sampleRate) {
    const wavHeader = Buffer.alloc(44);

    // RIFF header
    wavHeader.write('RIFF', 0);
    wavHeader.writeUInt32LE(36 + pcmBuffer.length, 4);
    wavHeader.write('WAVE', 8);

    // fmt chunk
    wavHeader.write('fmt ', 12);
    wavHeader.writeUInt32LE(16, 16); // chunk size
    wavHeader.writeUInt16LE(1, 20); // audio format (PCM)
    wavHeader.writeUInt16LE(1, 22); // num channels (mono)
    wavHeader.writeUInt32LE(sampleRate, 24); // sample rate
    wavHeader.writeUInt32LE(sampleRate * 2, 28); // byte rate
    wavHeader.writeUInt16LE(2, 32); // block align
    wavHeader.writeUInt16LE(16, 34); // bits per sample

    // data chunk
    wavHeader.write('data', 36);
    wavHeader.writeUInt32LE(pcmBuffer.length, 40);

    return Buffer.concat([wavHeader, pcmBuffer]);
  }
}

// Start the speech-to-speech bot
if (require.main === module) {
  const bot = new SpeechToSpeechBot();

  bot.start().then(() => {
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('🎙️  Speech-to-Speech AI Bot Ready!');
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('Features:');
    logger.info('  • Direct speech-to-speech processing');
    logger.info('  • OpenAI GPT-4 + Whisper + TTS');
    logger.info('  • Natural conversation flow');
    logger.info('  • Lower latency than pipeline bot');
    logger.info('  • Automatic silence detection');
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('');
    logger.info('Press # to end the call');
    logger.info('═══════════════════════════════════════════════════════');
  }).catch((error) => {
    logger.error('Failed to start speech-to-speech bot:', error);
    process.exit(1);
  });

  // Graceful shutdown
  const shutdown = async () => {
    logger.info('Shutting down speech-to-speech bot...');
    await bot.stop();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

module.exports = SpeechToSpeechBot;

