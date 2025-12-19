/**
 * Simple Conversation Bot - WORKS RELIABLY
 *
 * Buffers audio and processes complete utterances
 * No complex streaming - just reliable conversation
 */

const ExotelWSSServer = require('../src/core/server');
const AudioResampler = require('../src/core/utils/audioResampler');
const Logger = require('../src/core/utils/logger');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('../src/core/utils/botUtils');
const fs = require('fs');
const path = require('path');

const logger = new Logger('CONVERSATION-BOT');

// OpenAI SDK
let OpenAI;
try {
  OpenAI = require('openai').default;
} catch (error) {
  logger.error('OpenAI SDK not installed. Install with: npm install openai');
  process.exit(1);
}

class SimpleConversationBot extends ExotelWSSServer {
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

    logger.info('✅ Simple Conversation Bot initialized');
  }

  initializeSession(streamId) {
    const sampleRate = this.connections.get(streamId)?.sampleRate || 8000;

    return {
      streamId,
      sampleRate,
      audioBuffer: [],
      conversationHistory: [
        {
          role: 'system',
          content: 'You are a friendly and helpful voice assistant having a natural phone conversation. Speak naturally as if talking to a friend - use a conversational tone, vary your responses, and feel free to elaborate when helpful. Keep responses focused but natural (2-4 sentences). Be warm, engaging, and personable.'
        }
      ],
      chunkCount: 0,
      processingInterval: null,
      isProcessing: false,
      minChunksForProcessing: 80, // ~2 seconds of audio (more natural conversation)
      lastProcessedTime: Date.now(),
      silenceChunks: 0,
      lastAudioLevel: 0
    };
  }

  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    // Store sender in session for interval access
    session.sender = sender;
    session.streamId = streamId;
    this.sessions.set(streamId, session);

    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('🤖 Conversation Bot Session Started');
    logger.info(`   Stream: ${streamId.substring(0, 8)}`);
    logger.info(`   Sample Rate: ${session.sampleRate} Hz`);
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // Start periodic processing (every 2 seconds for responsiveness)
    // Use arrow function to maintain 'this' context and access session directly
    session.processingInterval = setInterval(() => {
      const currentSession = this.sessions.get(streamId);
      if (!currentSession) {
        logger.debug(`⏰ Periodic check: Session ${streamId.substring(0, 8)} no longer exists`);
        return;
      }

      // Process if we have minimum audio and not already processing
      if (currentSession.audioBuffer.length >= currentSession.minChunksForProcessing &&
          !currentSession.isProcessing) {

        const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
        logger.info(`⏰ Interval trigger: ${currentSession.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s) - processing now`);

        currentSession.lastProcessedTime = Date.now();
        this.processAudioBuffer(streamId, currentSession.sender).catch(err => {
          logger.error('Periodic processing error:', err.message);
        });
      }
    }, 2000); // Check every 2 seconds for responsiveness

    return {
      onStart: async (streamInfo) => {
        logger.info(`📞 Call started: ${streamInfo.call_sid}`);
        logger.info(`   From: ${streamInfo.from} → To: ${streamInfo.to}`);

        // OPTIMIZATION 1: Send early media to warm up audio pipeline immediately
        this.sendEarlyMedia(sender, session.sampleRate);

        // DON'T WAIT - Send greeting immediately in parallel with early media
        // This makes the bot start speaking immediately on call connect
        setImmediate(async () => {
          try {
            await this.sendVoiceMessage(
              streamId,
              sender,
              "Hi! I'm your assistant. How can I help you?"
            );
            logger.info('🎤 Greeting sent - ready for conversation');
          } catch (error) {
            logger.error('Error sending greeting:', error.message);
          }
        });
      },

      onMedia: (mediaData) => {
        session.chunkCount++;
        session.audioBuffer.push(mediaData.audioBuffer);

        // Calculate audio level for silence detection
        const audioLevel = this.calculateAudioLevel(mediaData.audioBuffer);
        const isSilent = audioLevel < 300; // Threshold for silence

        if (isSilent) {
          session.silenceChunks++;
        } else {
          session.silenceChunks = 0; // Reset on speech
        }

        // Log progress every 50 chunks
        if (session.chunkCount % 50 === 0) {
          const audioSeconds = (session.audioBuffer.length * 320) / (session.sampleRate * 2);
          logger.debug(`📦 Buffer: ${session.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s), silence: ${session.silenceChunks}`);
        }

        // IMMEDIATE TRIGGER: Process when we have enough audio AND detect silence (user stopped speaking)
        // This makes the bot responsive without waiting for the interval
        const hasEnoughAudio = session.audioBuffer.length >= session.minChunksForProcessing;
        const detectedPause = session.silenceChunks >= 15; // ~300ms of silence
        const notRecentlyProcessed = (Date.now() - session.lastProcessedTime) > 1500; // At least 1.5s between

        if (hasEnoughAudio && detectedPause && !session.isProcessing && notRecentlyProcessed) {
          const audioSeconds = (session.audioBuffer.length * 320) / (session.sampleRate * 2);
          logger.info(`🎤 Silence detected! Processing ${session.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s)...`);

          session.lastProcessedTime = Date.now();
          session.silenceChunks = 0; // Reset
          this.processAudioBuffer(streamId, session.sender).catch(err => {
            logger.error('Processing error:', err.message);
          });
        }
      },

      onMark: (markData) => {
        // Track when bot's audio finishes playing
        logger.debug(`✓ Mark received: ${markData.name} - audio playback complete`);
      },

      onDTMF: (dtmfData) => {
        logger.info(`🔢 DTMF: ${dtmfData.digit}`);

        if (dtmfData.digit === '#') {
          logger.info('User requested to end call');
          ws.close(1000, 'User ended call');
        }
      },

      onStop: (stopData) => {
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        logger.info('✓ Conversation ended');
        logger.info(`   Duration: ${(stopData.duration / 1000).toFixed(2)}s`);
        logger.info(`   Turns: ${Math.floor((session.conversationHistory.length - 1) / 2)}`);
        logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        // Clear interval
        if (session.processingInterval) {
          clearInterval(session.processingInterval);
        }

        this.sessions.delete(streamId);
      }
    };
  }

  async processAudioBuffer(streamId, sender) {
    const session = this.sessions.get(streamId);
    if (!session) {
      logger.warn('Session not found for processing');
      return;
    }

    if (session.audioBuffer.length === 0) {
      logger.debug('No audio to process');
      return;
    }

    if (session.isProcessing) {
      logger.debug('Already processing, skipping...');
      return;
    }

    session.isProcessing = true;
    const startTime = Date.now();

    try {
      // Combine buffered audio
      const audioChunks = session.audioBuffer.length;
      const combinedAudio = Buffer.concat(session.audioBuffer);
      session.audioBuffer = []; // Clear buffer immediately

      const audioSeconds = combinedAudio.length / (session.sampleRate * 2);
      logger.info(`🎤 Processing ${combinedAudio.length} bytes from ${audioChunks} chunks (${audioSeconds.toFixed(1)}s of audio)...`);

      // Verify minimum audio length for Whisper (0.1 seconds minimum)
      if (audioSeconds < 0.1) {
        logger.warn(`⚠️  Audio too short (${audioSeconds.toFixed(2)}s), need at least 0.1s for Whisper`);
        session.isProcessing = false;
        return;
      }

      // Step 1: Speech-to-Text (with timing)
      const sttStart = Date.now();
      const transcript = await this.transcribeAudio(combinedAudio, session.sampleRate);
      const sttTime = Date.now() - sttStart;

      // Filter out noise and very short/meaningless transcripts
      const cleanTranscript = transcript.trim();
      if (!cleanTranscript || cleanTranscript.length < 3 ||
          cleanTranscript.match(/^[.\s,!?]+$/) ||  // Just punctuation
          cleanTranscript.split(/\s+/).length < 2) {  // Single word or less
        logger.warn(`⚠️  Skipping noise/short transcript: "${cleanTranscript}"`);
        session.isProcessing = false;
        return;
      }

      logger.info(`👤 You: "${cleanTranscript}" (STT: ${sttTime}ms)`);

      // Add to conversation history
      session.conversationHistory.push({
        role: 'user',
        content: cleanTranscript
      });

      // Step 2: Get AI response (with timing)
      const llmStart = Date.now();
      const aiResponse = await this.getAIResponse(session);
      const llmTime = Date.now() - llmStart;

      logger.info(`🤖 Bot: "${aiResponse}" (LLM: ${llmTime}ms)`);

      // Add to conversation history
      session.conversationHistory.push({
        role: 'assistant',
        content: aiResponse
      });

      // Keep only last 10 exchanges (20 messages + system)
      if (session.conversationHistory.length > 21) {
        session.conversationHistory = [
          session.conversationHistory[0], // Keep system message
          ...session.conversationHistory.slice(-20)
        ];
      }

      // Step 3: Only clear if there's a long gap (avoid cutting off natural flow)
      // Don't clear too aggressively - let audio play naturally
      if ((Date.now() - session.lastProcessedTime) > 8000) {
        sender.sendClear();
        logger.debug('→ Cleared old audio (8s+ gap)');
      }

      // Step 4: Send voice response (with timing)
      const ttsStart = Date.now();
      await this.sendVoiceMessage(streamId, sender, aiResponse);
      const ttsTime = Date.now() - ttsStart;

      const totalTime = Date.now() - startTime;
      logger.info(`✅ Complete: STT ${sttTime}ms + LLM ${llmTime}ms + TTS ${ttsTime}ms = ${totalTime}ms total`);

    } catch (error) {
      logger.error('❌ Error processing audio:', error.message);
      logger.error('Stack trace:', error.stack);

      // Send error message
      try {
        logger.info('→ Sending error recovery message...');
        await this.sendVoiceMessage(
          streamId,
          sender,
          "I'm sorry, I didn't catch that. Could you please repeat?"
        );
      } catch (e) {
        logger.error('Failed to send error message:', e.message);
      }
    } finally {
      session.isProcessing = false;
      logger.debug('→ Processing complete, ready for next turn');
    }
  }

  async transcribeAudio(audioBuffer, sampleRate) {
    try {
      // Convert PCM to WAV
      const wavBuffer = this.createWavBuffer(audioBuffer, sampleRate);

      // Save to temp file
      const tempFile = path.join(__dirname, '..', 'logs', `audio_${Date.now()}.wav`);
      fs.writeFileSync(tempFile, wavBuffer);

      // Transcribe
      const transcription = await this.openai.audio.transcriptions.create({
        file: fs.createReadStream(tempFile),
        model: 'whisper-1',
        language: 'en'
      });

      // Cleanup
      fs.unlinkSync(tempFile);

      return transcription.text;
    } catch (error) {
      logger.error('Transcription error:', error.message);
      return '';
    }
  }

  async getAIResponse(session) {
    try {
      // Keep only last 10 messages to avoid token limits
      const recentHistory = [
        session.conversationHistory[0], // System message
        ...session.conversationHistory.slice(-9) // Last 9 messages
      ];

      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4-turbo-preview',
        messages: recentHistory,
        max_tokens: 100,
        temperature: 0.7
      });

      return completion.choices[0].message.content;
    } catch (error) {
      logger.error('LLM error:', error.message);
      return "I'm having trouble right now. Could you try again?";
    }
  }

  calculateAudioLevel(audioBuffer) {
    // Calculate average absolute value of audio samples
    let sum = 0;
    for (let i = 0; i < audioBuffer.length; i += 2) {
      const sample = audioBuffer.readInt16LE(i);
      sum += Math.abs(sample);
    }
    return sum / (audioBuffer.length / 2);
  }

  async sendVoiceMessage(streamId, sender, text) {
    const session = this.sessions.get(streamId);
    if (!session) return;

    try {
      // Generate speech
      const response = await this.openai.audio.speech.create({
        model: 'tts-1',
        voice: 'alloy',
        input: text,
        response_format: 'pcm'
      });

      const audioData = Buffer.from(await response.arrayBuffer());

      // Resample to match call sample rate
      const resampledAudio = AudioResampler.resample(
        audioData,
        24000, // OpenAI TTS outputs at 24kHz
        session.sampleRate
      );

      // OPTIMIZATION 2: Send media in optimal chunks (100ms = 3.2KB at 8kHz)
      // Benefits: Faster streamhandler stabilization, no buffering delays, no audio gaps
      this.sendMediaInChunks(sender, resampledAudio, session.sampleRate);

      // OPTIMIZATION 3: Use Mark event to track when audio finishes playing
      const markName = `msg_${Date.now()}`;
      sender.sendMark(markName);

      logger.debug(`🔊 Voice message sent with mark: ${markName}`);
    } catch (error) {
      logger.error('TTS error:', error.message);
      throw error;
    }
  }

  /**
   * OPTIMIZATION 1: Send early media to warm up audio pipeline
   * Reduces first-audio latency by 200-400ms
   */
  sendEarlyMedia(sender, sampleRate) {
    // Send 30ms of silence (optimal: 20-40ms)
    const durationMs = 30;
    const bytesPerMs = (sampleRate * 2) / 1000; // 16-bit audio = 2 bytes per sample
    const silenceSize = Math.floor(durationMs * bytesPerMs);

    // Ensure it's a multiple of 320 bytes
    const adjustedSize = Math.ceil(silenceSize / 320) * 320;
    const silence = Buffer.alloc(adjustedSize, 0);

    sender.sendMedia(silence);
    logger.debug(`🎵 Early media sent (${adjustedSize} bytes) - pipeline warmed up`);
  }

  /**
   * OPTIMIZATION 2: Send media in stable 100ms chunks (≥3.2KB)
   * Ensures fast streamhandler stabilization and no audio gaps
   */
  sendMediaInChunks(sender, audioBuffer, sampleRate) {
    // Calculate optimal chunk size (100ms)
    const chunkDurationMs = 100;
    const bytesPerMs = (sampleRate * 2) / 1000; // 16-bit = 2 bytes per sample
    const idealChunkSize = Math.floor(chunkDurationMs * bytesPerMs);

    // Ensure chunk size is multiple of 320 bytes (20ms frames)
    const chunkSize = Math.ceil(idealChunkSize / 320) * 320;

    // Send audio in chunks
    let offset = 0;
    let chunkCount = 0;

    while (offset < audioBuffer.length) {
      const remainingBytes = audioBuffer.length - offset;
      const currentChunkSize = Math.min(chunkSize, remainingBytes);

      // Only send if it's at least 320 bytes or it's the last chunk
      if (currentChunkSize >= 320 || offset + currentChunkSize === audioBuffer.length) {
        const chunk = audioBuffer.slice(offset, offset + currentChunkSize);
        sender.sendMedia(chunk);
        chunkCount++;
        offset += currentChunkSize;
      } else {
        // Skip very small final chunk
        break;
      }
    }

    logger.debug(`📤 Sent ${chunkCount} optimal chunks (${chunkSize} bytes each)`);
  }

  createWavBuffer(pcmBuffer, sampleRate) {
    const wavHeader = Buffer.alloc(44);

    // RIFF header
    wavHeader.write('RIFF', 0);
    wavHeader.writeUInt32LE(36 + pcmBuffer.length, 4);
    wavHeader.write('WAVE', 8);

    // fmt chunk
    wavHeader.write('fmt ', 12);
    wavHeader.writeUInt32LE(16, 16);
    wavHeader.writeUInt16LE(1, 20); // PCM
    wavHeader.writeUInt16LE(1, 22); // Mono
    wavHeader.writeUInt32LE(sampleRate, 24);
    wavHeader.writeUInt32LE(sampleRate * 2, 28);
    wavHeader.writeUInt16LE(2, 32);
    wavHeader.writeUInt16LE(16, 34);

    // data chunk
    wavHeader.write('data', 36);
    wavHeader.writeUInt32LE(pcmBuffer.length, 40);

    return Buffer.concat([wavHeader, pcmBuffer]);
  }
}

// Start the bot
if (require.main === module) {
  const bot = new SimpleConversationBot();

  bot.start().then(() => {
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('🎙️  Simple Conversation Bot Ready!');
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('How it works:');
    logger.info('  • Buffers your speech for 3 seconds');
    logger.info('  • Transcribes with Whisper');
    logger.info('  • Responds with GPT-4');
    logger.info('  • Speaks back with natural voice');
    logger.info('═══════════════════════════════════════════════════════');
    logger.info('Just speak naturally - pauses are OK!');
    logger.info('Press # to end the call');
    logger.info('═══════════════════════════════════════════════════════');
  }).catch((error) => {
    logger.error('Failed to start bot:', error);
    process.exit(1);
  });

  const shutdown = async () => {
    logger.info('Shutting down...');
    await bot.stop();
    process.exit(0);
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

module.exports = SimpleConversationBot;

