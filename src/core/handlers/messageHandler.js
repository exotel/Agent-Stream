const Logger = require('../utils/logger');
const EventLogger = require('../utils/eventLogger');
const AudioUtils = require('../utils/audio');
const config = require('../config');

/**
 * Handles incoming messages from Exotel
 */
class MessageHandler {
  constructor(streamId) {
    this.streamId = streamId;
    this.logger = new Logger(`STREAM-${streamId.substring(0, 8)}`);
    this.eventLogger = new EventLogger(streamId);
    this.streamInfo = null;
    this.sequenceNumber = 0;
    this.mediaChunkCount = 0;
    this.startTime = Date.now();
  }

  /**
   * Process incoming message from Exotel
   * @param {object} ws - WebSocket connection
   * @param {string} message - JSON string message
   * @param {function} onMedia - Callback for media processing
   * @param {function} onDTMF - Callback for DTMF events
   * @param {function} onStop - Callback for stream stop
   */
  handleMessage(ws, message, callbacks = {}) {
    try {
      const data = JSON.parse(message);
      const { event } = data;

      this.logger.debug(`Received event: ${event}`);

      switch (event) {
        case 'connected':
          this.handleConnected(data);
          break;

        case 'start':
          this.handleStart(data, callbacks.onStart);
          break;

        case 'media':
          this.handleMedia(data, callbacks.onMedia);
          break;

        case 'dtmf':
          this.handleDTMF(data, callbacks.onDTMF);
          break;

        case 'stop':
          this.handleStop(data, callbacks.onStop);
          break;

        case 'mark':
          this.handleMark(data, callbacks.onMark);
          break;

        default:
          this.logger.warn(`Unknown event type: ${event}`);
      }
    } catch (error) {
      this.logger.error('Error parsing message:', error.message);
    }
  }

  /**
   * Handle connected event
   */
  handleConnected(data) {
    this.logger.info('✓ WebSocket connection established with Exotel');
    this.eventLogger.logBotEvent('connected', { event: 'connected' });
  }

  /**
   * Handle start event
   */
  handleStart(data, callback) {
    this.streamInfo = data.start;
    this.sequenceNumber = parseInt(data.sequence_number) || 0;

    const { call_sid, account_sid, from, to, media_format, custom_parameters } = this.streamInfo;

    // Log with EventLogger for detailed tracking
    this.eventLogger.logStreamStart(this.streamInfo);

    // Validate sample rate
    const sampleRate = parseInt(media_format?.sample_rate);
    if (!AudioUtils.validateSampleRate(sampleRate)) {
      this.logger.warn(`⚠️  Unsupported sample rate: ${sampleRate}. Supported rates: ${config.audio.supportedSampleRates.join(', ')}`);
      this.eventLogger.logError(
        new Error(`Unsupported sample rate: ${sampleRate}`),
        { supportedRates: config.audio.supportedSampleRates }
      );
    }

    if (callback) {
      callback(this.streamInfo);
    }
  }

  /**
   * Handle media event
   */
  handleMedia(data, callback) {
    this.mediaChunkCount++;
    const { chunk, timestamp, payload } = data.media;

    // Decode audio from base64
    const audioBuffer = AudioUtils.decodeAudio(payload);
    const duration = AudioUtils.calculateDuration(audioBuffer.length, this.getSampleRate());

    const mediaData = {
      chunk: parseInt(chunk),
      timestamp: parseInt(timestamp),
      audioBuffer,
      duration,
      sequenceNumber: data.sequence_number
    };

    // Log with EventLogger
    this.eventLogger.logMedia(mediaData, {
      totalChunks: this.mediaChunkCount,
      payloadLength: payload.length
    });

    if (callback) {
      callback(mediaData);
    }
  }

  /**
   * Handle DTMF event
   */
  handleDTMF(data, callback) {
    const { digit, duration } = data.dtmf;

    const dtmfData = {
      digit,
      duration: parseInt(duration),
      sequenceNumber: data.sequence_number
    };

    // Log with EventLogger
    this.eventLogger.logDTMF(dtmfData);

    if (callback) {
      callback(dtmfData);
    }
  }

  /**
   * Handle stop event
   */
  handleStop(data, callback) {
    const { call_sid, account_sid, reason } = data.stop;
    const duration = Date.now() - this.startTime;

    const stopData = {
      callSid: call_sid,
      accountSid: account_sid,
      reason,
      totalChunks: this.mediaChunkCount,
      duration
    };

    // Log with EventLogger
    this.eventLogger.logStreamStop(stopData);

    if (callback) {
      callback(stopData);
    }
  }

  /**
   * Handle mark event
   */
  handleMark(data, callback) {
    const { name } = data.mark;

    const markData = {
      name,
      sequenceNumber: data.sequence_number
    };

    // Log with EventLogger
    this.eventLogger.logMark(markData);

    if (callback) {
      callback(markData);
    }
  }

  /**
   * Get current sample rate from stream info
   */
  getSampleRate() {
    return parseInt(this.streamInfo?.media_format?.sample_rate) || config.audio.defaultSampleRate;
  }

  /**
   * Get stream statistics
   */
  getStats() {
    return {
      streamId: this.streamId,
      mediaChunkCount: this.mediaChunkCount,
      duration: Date.now() - this.startTime,
      streamInfo: this.streamInfo
    };
  }
}

module.exports = MessageHandler;

