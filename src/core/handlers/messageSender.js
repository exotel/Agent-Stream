const Logger = require('../utils/logger');
const AudioUtils = require('../utils/audio');

/**
 * Handles sending messages to Exotel (for bidirectional streaming)
 */
class MessageSender {
  constructor(ws, streamId, eventLogger = null) {
    this.ws = ws;
    this.streamId = streamId;
    this.logger = new Logger(`SENDER-${streamId.substring(0, 8)}`);
    this.eventLogger = eventLogger;
    this.sequenceNumber = 0;
    this.mediaChunksSent = 0;
  }

  /**
   * Send media message to Exotel
   * @param {Buffer} audioBuffer - PCM audio buffer
   * @param {number} timestamp - Timestamp in milliseconds
   * @param {boolean} skipValidation - Skip chunk size validation (for low-latency streaming)
   */
  sendMedia(audioBuffer, timestamp = null, skipValidation = false) {
    // Validate chunk size (unless explicitly skipped for low-latency mode)
    if (!skipValidation) {
      const validation = AudioUtils.validateChunkSize(audioBuffer.length);
      if (!validation.valid) {
        // Only warn once per 100 chunks to avoid log spam
        if (this.mediaChunksSent % 100 === 0) {
          this.logger.warn(`⚠️  Chunk size validation warning (x100): ${validation.reason}`);
        }
      }
    }

    // Encode audio to base64
    const payload = AudioUtils.encodeAudio(audioBuffer);

    this.sequenceNumber++;
    this.mediaChunksSent++;

    const actualTimestamp = timestamp || Date.now();

    const message = {
      event: 'media',
      sequence_number: this.sequenceNumber.toString(),
      stream_sid: this.streamId,
      media: {
        chunk: this.mediaChunksSent.toString(),
        timestamp: actualTimestamp.toString(),
        payload: payload
      }
    };

    this._send(message);

    // Log with EventLogger
    if (this.eventLogger) {
      this.eventLogger.logOutgoingMedia(audioBuffer, actualTimestamp, this.mediaChunksSent);
    }
  }

  /**
   * Send mark message to Exotel
   * Used to track when audio has been processed
   * @param {string} name - Label for the mark
   */
  sendMark(name) {
    this.sequenceNumber++;

    const message = {
      event: 'mark',
      sequence_number: this.sequenceNumber.toString(),
      stream_sid: this.streamId,
      mark: {
        name: name
      }
    };

    this._send(message);
    this.logger.debug(`📤 Sent mark: ${name}`);

    // Log with EventLogger
    if (this.eventLogger) {
      this.eventLogger.logMark({ name, sequenceNumber: this.sequenceNumber }, 'sent_to_exotel');
    }
  }

  /**
   * Send clear message to Exotel
   * Clears audio data that was sent but not yet played
   */
  sendClear() {
    const message = {
      event: 'clear',
      stream_sid: this.streamId
    };

    this._send(message);
    this.logger.info('📤 Sent clear event');

    // Log with EventLogger
    if (this.eventLogger) {
      this.eventLogger.logClear('clear_requested_by_bot');
    }
  }

  /**
   * Internal method to send message
   */
  _send(message) {
    try {
      if (this.ws.readyState === this.ws.OPEN) {
        this.ws.send(JSON.stringify(message));

        if (message.event !== 'media' || this.mediaChunksSent % 100 === 0) {
          this.logger.debug(`Sent ${message.event} event (seq: ${message.sequence_number})`);
        }
      } else {
        this.logger.error('WebSocket is not open, cannot send message');
      }
    } catch (error) {
      this.logger.error('Error sending message:', error.message);
    }
  }

  /**
   * Get sender statistics
   */
  getStats() {
    return {
      streamId: this.streamId,
      mediaChunksSent: this.mediaChunksSent,
      sequenceNumber: this.sequenceNumber
    };
  }
}

module.exports = MessageSender;

