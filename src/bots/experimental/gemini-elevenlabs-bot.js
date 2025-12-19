/**
 * Gemini + ElevenLabs Voice Bot
 *
 * End-to-end voice AI using:
 * - Google Gemini 2.5 Flash (Audio understanding + LLM)
 * - ElevenLabs (Text-to-Speech)
 *
 * No OpenAI required!
 */

const ExotelWSSServer = require('../src/server');
const AudioResampler = require('../src/utils/audioResampler');
const Logger = require('../src/utils/logger');
const https = require('https');

const logger = new Logger('GEMINI-ELEVENLABS');

// Google Generative AI SDK
let GoogleGenerativeAI;
try {
  const { GoogleGenerativeAI: SDK } = require('@google/generative-ai');
  GoogleGenerativeAI = SDK;
} catch (error) {
  logger.error('Google Generative AI SDK not installed. Install with: npm install @google/generative-ai');
  process.exit(1);
}

// Audio format constants
const AUDIO_FORMAT = {
  EXOTEL_SAMPLE_RATE: 8000,
  ELEVENLABS_SAMPLE_RATE: 22050, // ElevenLabs default output
  GEMINI_SAMPLE_RATE: 16000
};

class GeminiElevenLabsBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();

    // Check API keys
    this.geminiApiKey = process.env.GEMINI_API_KEY;
    this.elevenLabsApiKey = process.env.ELEVENLABS_API_KEY;
    this.elevenLabsVoiceId = process.env.ELEVENLABS_VOICE_ID || 'EXAVITQu4vr4xnSDxMaL'; // Default: Sarah

    if (!this.geminiApiKey) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ GEMINI_API_KEY not configured!');
      logger.error('Add to .env: GEMINI_API_KEY=your_key');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    if (!this.elevenLabsApiKey) {
      logger.error('═══════════════════════════════════════════════════════');
      logger.error('❌ ELEVENLABS_API_KEY not configured!');
      logger.error('Add to .env: ELEVENLABS_API_KEY=your_key');
      logger.error('═══════════════════════════════════════════════════════');
      process.exit(1);
    }

    // Initialize Gemini
    this.genAI = new GoogleGenerativeAI(this.geminiApiKey);

    logger.info('✅ Gemini + ElevenLabs Bot initialized');
    logger.info('   AI: Gemini 2.5 Flash');
    logger.info(`   Voice: ElevenLabs (${this.elevenLabsVoiceId})`);
    logger.info(`   Gemini Key: ${this.geminiApiKey.substring(0, 10)}...`);
    logger.info(`   ElevenLabs Key: ${this.elevenLabsApiKey.substring(0, 10)}...`);
  }

  initializeSession(streamId) {
    const sampleRate = this.connections.get(streamId)?.sampleRate || AUDIO_FORMAT.EXOTEL_SAMPLE_RATE;

    return {
      streamId,
      sampleRate,
      audioBuffer: [],
      isProcessing: false,
      conversationHistory: [],
      silenceCounter: 0,
      silenceThreshold: 15, // ~300ms of silence
      minAudioChunks: 80, // ~2 seconds minimum
      lastActivity: Date.now(),
      chunkCount: 0,
      processingInterval: null,
      lastProcessedTime: Date.now(),
      sender: null
    };
  }

  /**
   * Generate speech using ElevenLabs API
   */
  async textToSpeech(text) {
    return new Promise((resolve, reject) => {
      const postData = JSON.stringify({
        text: text,
        model_id: 'eleven_turbo_v2_5', // Fast model
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
          style: 0.0,
          use_speaker_boost: true
        }
      });

      const options = {
        hostname: 'api.elevenlabs.io',
        port: 443,
        path: `/v1/text-to-speech/${this.elevenLabsVoiceId}?output_format=pcm_22050`,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'xi-api-key': this.elevenLabsApiKey,
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const req = https.request(options, (res) => {
        const chunks = [];

        res.on('data', (chunk) => chunks.push(chunk));

        res.on('end', () => {
          if (res.statusCode === 200) {
            resolve(Buffer.concat(chunks));
          } else {
            const errorBody = Buffer.concat(chunks).toString();
            reject(new Error(`ElevenLabs API error ${res.statusCode}: ${errorBody}`));
          }
        });
      });

      req.on('error', reject);
      req.write(postData);
      req.end();
    });
  }

  getMessageCallbacks(streamId, ws, sender) {
    const session = this.initializeSession(streamId);
    session.sender = sender;
    this.sessions.set(streamId, session);

    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('🤖 Gemini + ElevenLabs Session Started');
    logger.info(`   Stream: ${streamId.substring(0, 8)}`);
    logger.info('   AI: Gemini 2.5 Flash');
    logger.info('   Voice: ElevenLabs TTS');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    // Periodic processing (backup)
    session.processingInterval = setInterval(() => {
      const currentSession = this.sessions.get(streamId);
      if (!currentSession) return;

      if (currentSession.audioBuffer.length >= currentSession.minAudioChunks &&
          !currentSession.isProcessing &&
          (Date.now() - currentSession.lastProcessedTime) > 1500) {

        logger.info(`⏰ Interval trigger: ${currentSession.audioBuffer.length} chunks`);
        currentSession.lastProcessedTime = Date.now();
        this.processAudio(streamId).catch(err => {
          logger.error('Interval processing error:', err.message);
        });
      }
    }, 2000);

    return {
      onStart: async (streamInfo) => {
        logger.info(`📞 Call started: ${streamInfo.call_sid}`);
        logger.info(`   From: ${streamInfo.from} → To: ${streamInfo.to}`);

        // Send greeting
        setImmediate(async () => {
          try {
            await this.sendGreeting(streamId);
            logger.info('🎤 Greeting sent - ready for conversation');
          } catch (error) {
            logger.error('Error sending greeting:', error.message);
          }
        });
      },

      onMedia: (mediaData) => {
        const currentSession = this.sessions.get(streamId);
        if (!currentSession) return;

        currentSession.lastActivity = Date.now();
        currentSession.chunkCount++;

        try {
          const audioBuffer = mediaData.audioBuffer;
          const audioLevel = this.calculateAudioLevel(audioBuffer);
          const isSilent = audioLevel < 300;

          if (isSilent) {
            currentSession.silenceCounter++;
          } else {
            currentSession.silenceCounter = 0;
            currentSession.audioBuffer.push(audioBuffer);
          }

          // Log every 50 chunks
          if (currentSession.chunkCount % 50 === 0) {
            const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
            logger.debug(`📦 Buffer: ${currentSession.audioBuffer.length} chunks (${audioSeconds.toFixed(1)}s)`);
          }

          const hasEnoughAudio = currentSession.audioBuffer.length >= currentSession.minAudioChunks;
          const detectedPause = currentSession.silenceCounter >= currentSession.silenceThreshold;
          const notRecentlyProcessed = (Date.now() - currentSession.lastProcessedTime) > 1500;

          if (hasEnoughAudio && detectedPause && !currentSession.isProcessing && notRecentlyProcessed) {
            const audioSeconds = (currentSession.audioBuffer.length * 320) / (currentSession.sampleRate * 2);
            logger.info(`🎤 Silence detected! Processing ${audioSeconds.toFixed(1)}s of audio...`);

            currentSession.lastProcessedTime = Date.now();
            currentSession.silenceCounter = 0;

            this.processAudio(streamId).catch(err => {
              logger.error('Processing error:', err.message);
            });
          }
        } catch (error) {
          logger.error('Error processing media:', error.message);
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
        logger.info('✓ Session ended');
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

  async sendGreeting(streamId) {
    const session = this.sessions.get(streamId);
    if (!session) return;

    try {
      const greeting = "Hi! I'm your AI assistant powered by Gemini. How can I help you today?";

      const ttsStart = Date.now();
      const audioData = await this.textToSpeech(greeting);
      const ttsTime = Date.now() - ttsStart;

      logger.info(`🔊 TTS completed in ${ttsTime}ms (${audioData.length} bytes)`);

      // Resample from 22050Hz to 8000Hz for Exotel
      const resampledAudio = AudioResampler.resample(
        audioData,
        AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE,
        session.sampleRate
      );

      // Send in chunks
      session.sender.sendClear();
      const chunkSize = 3200; // 200ms at 8kHz
      for (let i = 0; i < resampledAudio.length; i += chunkSize) {
        const chunk = resampledAudio.slice(i, Math.min(i + chunkSize, resampledAudio.length));
        session.sender.sendMedia(chunk);
      }
      session.sender.sendMark(`greeting-complete-${Date.now()}`);

    } catch (error) {
      logger.error('Error sending greeting:', error.message);
    }
  }

  async processAudio(streamId) {
    const session = this.sessions.get(streamId);
    if (!session || session.audioBuffer.length === 0) return;
    if (session.isProcessing) return;

    session.isProcessing = true;
    const processingStartTime = Date.now();

    try {
      // Combine audio buffer
      const combinedAudio = Buffer.concat(session.audioBuffer);
      const audioChunks = session.audioBuffer.length;
      session.audioBuffer = [];

      const audioSeconds = combinedAudio.length / (session.sampleRate * 2);
      logger.info(`🎤 Processing ${audioChunks} chunks (${audioSeconds.toFixed(1)}s)...`);

      // Resample from 8kHz to 16kHz for Gemini
      const resampledForGemini = AudioResampler.resample(
        combinedAudio,
        session.sampleRate,
        AUDIO_FORMAT.GEMINI_SAMPLE_RATE
      );

      // Create WAV buffer for Gemini
      const wavBuffer = this.createWavBuffer(resampledForGemini, AUDIO_FORMAT.GEMINI_SAMPLE_RATE);
      const base64Audio = wavBuffer.toString('base64');

      // Send to Gemini
      const geminiStart = Date.now();
      const model = this.genAI.getGenerativeModel({
        model: 'gemini-2.5-flash',
        systemInstruction: 'You are a helpful voice assistant. Keep responses concise (1-2 sentences). Be friendly and conversational. If you cannot understand the audio, politely ask the user to repeat.'
      });

      const result = await model.generateContent([
        {
          inlineData: {
            mimeType: 'audio/wav',
            data: base64Audio
          }
        },
        'Listen to this audio and respond naturally to what the user said. Keep your response brief and conversational.'
      ]);

      const response = await result.response;
      const aiResponse = response.text();
      const geminiTime = Date.now() - geminiStart;

      if (!aiResponse || aiResponse.trim().length < 2) {
        logger.warn('⚠️  Empty Gemini response');
        session.isProcessing = false;
        return;
      }

      logger.info(`🤖 Gemini (${geminiTime}ms): "${aiResponse}"`);

      // Store in history
      session.conversationHistory.push({ role: 'user', audio: true });
      session.conversationHistory.push({ role: 'model', text: aiResponse });

      // Generate speech with ElevenLabs
      const ttsStart = Date.now();
      const responseAudio = await this.textToSpeech(aiResponse);
      const ttsTime = Date.now() - ttsStart;

      logger.info(`🔊 ElevenLabs TTS (${ttsTime}ms): ${responseAudio.length} bytes`);

      // Resample from 22050Hz to 8000Hz for Exotel
      const resampledAudio = AudioResampler.resample(
        responseAudio,
        AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE,
        session.sampleRate
      );

      // Send to Exotel
      session.sender.sendClear();
      const chunkSize = 3200;
      let chunksSent = 0;
      for (let i = 0; i < resampledAudio.length; i += chunkSize) {
        const chunk = resampledAudio.slice(i, Math.min(i + chunkSize, resampledAudio.length));
        session.sender.sendMedia(chunk);
        chunksSent++;
      }
      session.sender.sendMark(`response-complete-${Date.now()}`);

      const totalTime = Date.now() - processingStartTime;
      const audioSecs = resampledAudio.length / (session.sampleRate * 2);

      logger.info(`🔊 Response: ${chunksSent} chunks, ${audioSecs.toFixed(1)}s audio`);
      logger.info(`✅ Total: Gemini ${geminiTime}ms + TTS ${ttsTime}ms = ${totalTime}ms`);

    } catch (error) {
      logger.error('Processing error:', error.message);

      // Send error message
      try {
        const errorAudio = await this.textToSpeech('Sorry, I had trouble understanding that. Could you please repeat?');
        const resampled = AudioResampler.resample(errorAudio, AUDIO_FORMAT.ELEVENLABS_SAMPLE_RATE, session.sampleRate);
        session.sender.sendMedia(resampled);
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
    wavHeader.writeUInt16LE(1, 20); // PCM
    wavHeader.writeUInt16LE(1, 22); // Mono
    wavHeader.writeUInt32LE(sampleRate, 24);
    wavHeader.writeUInt32LE(sampleRate * 2, 28);
    wavHeader.writeUInt16LE(2, 32);
    wavHeader.writeUInt16LE(16, 34); // 16-bit
    wavHeader.write('data', 36);
    wavHeader.writeUInt32LE(dataSize, 40);

    return Buffer.concat([wavHeader, pcmBuffer]);
  }
}

// Start server
const port = process.env.PORT || 5001;
const bot = new GeminiElevenLabsBot();

bot.start(port).then(() => {
  logger.info('');
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('🤖 Gemini + ElevenLabs Voice Bot Ready!');
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('');
  logger.info('🔧 Powered by:');
  logger.info('   • Google Gemini 2.5 Flash (Audio + LLM)');
  logger.info('   • ElevenLabs (Text-to-Speech)');
  logger.info('');
  logger.info('📞 Flow:');
  logger.info('   ┌──────────┐    ┌────────────┐    ┌────────────┐');
  logger.info('   │  Exotel  │ → │  Gemini    │ → │ ElevenLabs │');
  logger.info('   │  Audio   │    │  STT+LLM   │    │    TTS     │');
  logger.info('   └──────────┘    └────────────┘    └────────────┘');
  logger.info('      8kHz           16kHz            22kHz→8kHz');
  logger.info('');
  logger.info('⚡ Features:');
  logger.info('   • Gemini audio understanding (no separate STT)');
  logger.info('   • High-quality ElevenLabs voices');
  logger.info('   • Silence detection for natural conversation');
  logger.info('');
  logger.info('═══════════════════════════════════════════════════════');
  logger.info('Press Ctrl+C to stop');
  logger.info('═══════════════════════════════════════════════════════');
}).catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});

module.exports = GeminiElevenLabsBot;

