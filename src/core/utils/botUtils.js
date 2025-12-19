/**
 * Bot Utilities
 *
 * Shared utilities for all voice bots incorporating learnings:
 * 1. Proper audio chunking (3200 bytes minimum)
 * 2. Turn-taking state management
 * 3. Barge-in handling
 * 4. Audio level calculation for silence detection
 * 5. Early media for connection warmup
 */

const Logger = require('./logger');

const logger = new Logger('BOT-UTILS');

// Exotel audio constants
const EXOTEL_CONSTANTS = {
  SAMPLE_RATE: 8000,              // 8kHz
  BITS_PER_SAMPLE: 16,            // 16-bit
  CHANNELS: 1,                    // Mono
  CHUNK_DURATION_MS: 20,          // 20ms per chunk from Exotel
  MIN_CHUNK_SIZE: 3200,           // Minimum chunk size for sending (200ms)
  BYTES_PER_CHUNK: 320,           // 20ms at 8kHz, 16-bit = 320 bytes
  SILENCE_THRESHOLD: 300          // Audio level below this = silence
};

/**
 * Session state machine for proper turn-taking
 */
class SessionState {
  constructor(streamId) {
    this.streamId = streamId;

    // Processing state
    this.isProcessing = false;      // AI processing in progress
    this.isBotSpeaking = false;     // Bot audio being sent
    this.isUserSpeaking = false;    // User currently speaking

    // Audio buffer
    this.audioBuffer = [];          // Incoming audio chunks
    this.silenceCounter = 0;        // Consecutive silent chunks

    // Timing
    this.lastActivity = Date.now();
    this.lastProcessedTime = Date.now();
    this.processingCooldown = 1000; // Min time between processing

    // Thresholds (tunable)
    this.silenceThreshold = 10;     // ~200ms of silence triggers processing
    this.minAudioChunks = 40;       // ~800ms minimum speech

    // Conversation
    this.conversationHistory = [];
    this.turnCount = 0;
  }

  /**
   * Check if we can start processing
   */
  canProcess() {
    const hasEnoughAudio = this.audioBuffer.length >= this.minAudioChunks;
    const detectedPause = this.silenceCounter >= this.silenceThreshold;
    const notRecentlyProcessed = (Date.now() - this.lastProcessedTime) > this.processingCooldown;

    return hasEnoughAudio &&
           detectedPause &&
           !this.isProcessing &&
           !this.isBotSpeaking &&
           notRecentlyProcessed;
  }

  /**
   * Start processing (call synchronously before async work)
   * Returns the audio to process, or null if can't process
   */
  startProcessing() {
    if (!this.canProcess()) return null;

    // Lock immediately (synchronous)
    this.isProcessing = true;
    this.lastProcessedTime = Date.now();
    this.silenceCounter = 0;

    // Copy and clear buffer atomically
    const audioToProcess = [...this.audioBuffer];
    this.audioBuffer = [];

    this.turnCount++;

    return audioToProcess;
  }

  /**
   * Finish processing
   */
  finishProcessing() {
    this.isProcessing = false;
  }

  /**
   * Start speaking (bot is outputting audio)
   */
  startSpeaking() {
    this.isBotSpeaking = true;
  }

  /**
   * Stop speaking
   */
  stopSpeaking() {
    this.isBotSpeaking = false;
  }

  /**
   * Handle barge-in (user interrupted bot)
   */
  handleBargeIn() {
    this.isBotSpeaking = false;
    this.isProcessing = false;
    this.audioBuffer = [];
    this.silenceCounter = 0;
  }
}

/**
 * Audio utilities
 */
class AudioUtils {
  /**
   * Calculate audio level for silence detection
   * @param {Buffer} audioBuffer - PCM audio buffer
   * @returns {number} Average absolute amplitude
   */
  static calculateAudioLevel(audioBuffer) {
    if (!audioBuffer || audioBuffer.length < 2) return 0;

    let sum = 0;
    const samples = audioBuffer.length / 2;

    for (let i = 0; i < audioBuffer.length - 1; i += 2) {
      const sample = audioBuffer.readInt16LE(i);
      sum += Math.abs(sample);
    }

    return sum / samples;
  }

  /**
   * Check if audio chunk is silent
   * @param {Buffer} audioBuffer - PCM audio buffer
   * @param {number} threshold - Silence threshold (default: 300)
   * @returns {boolean} True if silent
   */
  static isSilent(audioBuffer, threshold = EXOTEL_CONSTANTS.SILENCE_THRESHOLD) {
    return this.calculateAudioLevel(audioBuffer) < threshold;
  }

  /**
   * Send audio in proper chunks to Exotel
   * @param {Object} sender - MessageSender instance
   * @param {Buffer} audioBuffer - Audio to send
   * @param {number} chunkSize - Chunk size (default: 3200)
   * @returns {number} Number of chunks sent
   */
  static sendAudioChunked(sender, audioBuffer, chunkSize = EXOTEL_CONSTANTS.MIN_CHUNK_SIZE) {
    if (!audioBuffer || audioBuffer.length === 0) return 0;

    let chunksSent = 0;

    for (let i = 0; i < audioBuffer.length; i += chunkSize) {
      const chunk = audioBuffer.slice(i, Math.min(i + chunkSize, audioBuffer.length));

      // Pad final chunk if needed
      if (chunk.length < chunkSize && chunk.length > 0) {
        const paddedChunk = Buffer.alloc(chunkSize, 0);
        chunk.copy(paddedChunk);
        sender.sendMedia(paddedChunk);
      } else {
        sender.sendMedia(chunk);
      }
      chunksSent++;
    }

    return chunksSent;
  }

  /**
   * Send early media (silence) to establish audio path
   * @param {Object} sender - MessageSender instance
   */
  static sendEarlyMedia(sender) {
    const silence = Buffer.alloc(EXOTEL_CONSTANTS.MIN_CHUNK_SIZE, 0);
    sender.sendMedia(silence);
  }

  /**
   * Create WAV buffer from PCM data
   * @param {Buffer} pcmBuffer - Raw PCM data
   * @param {number} sampleRate - Sample rate
   * @returns {Buffer} WAV buffer
   */
  static createWavBuffer(pcmBuffer, sampleRate = 8000) {
    const header = Buffer.alloc(44);
    const dataSize = pcmBuffer.length;
    const fileSize = dataSize + 36;

    // RIFF header
    header.write('RIFF', 0);
    header.writeUInt32LE(fileSize, 4);
    header.write('WAVE', 8);

    // fmt chunk
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16);      // Chunk size
    header.writeUInt16LE(1, 20);       // Audio format (PCM)
    header.writeUInt16LE(1, 22);       // Channels
    header.writeUInt32LE(sampleRate, 24);
    header.writeUInt32LE(sampleRate * 2, 28);  // Byte rate
    header.writeUInt16LE(2, 32);       // Block align
    header.writeUInt16LE(16, 34);      // Bits per sample

    // data chunk
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40);

    return Buffer.concat([header, pcmBuffer]);
  }
}

/**
 * Barge-in handler
 */
class BargeInHandler {
  /**
   * Handle user interruption
   * @param {SessionState} state - Session state
   * @param {Object} sender - MessageSender
   * @param {Object} aiConnection - AI WebSocket connection (optional)
   */
  static handle(state, sender, aiConnection = null) {
    logger.info('⚡ BARGE-IN: User interrupted bot!');

    // Stop audio playback
    sender.sendClear();

    // Update state
    state.handleBargeIn();

    // Cancel AI response if possible
    if (aiConnection && aiConnection.readyState === 1) {
      try {
        // OpenAI Realtime
        if (aiConnection.send) {
          aiConnection.send(JSON.stringify({ type: 'response.cancel' }));
        }
      } catch (e) {
        // Ignore
      }
    }
  }

  /**
   * Check if should trigger barge-in
   * @param {SessionState} state - Session state
   * @param {Buffer} audioBuffer - Incoming audio
   * @returns {boolean} True if barge-in should trigger
   */
  static shouldTrigger(state, audioBuffer) {
    return state.isBotSpeaking && !AudioUtils.isSilent(audioBuffer);
  }
}

module.exports = {
  EXOTEL_CONSTANTS,
  SessionState,
  AudioUtils,
  BargeInHandler
};

