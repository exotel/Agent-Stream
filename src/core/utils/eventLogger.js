const Logger = require('./logger');
const fs = require('fs');
const path = require('path');
const config = require('../config');

/**
 * Enhanced event logging with structured data
 * Helps debug WebSocket events, audio processing, and bot behavior
 */
class EventLogger {
  constructor(streamId, callSid = null) {
    this.streamId = streamId;
    this.callSid = callSid;
    this.logger = new Logger(`EVENT-${streamId.substring(0, 8)}`);
    this.events = [];
    this.startTime = Date.now();
    this.logToFile = config.logging.logEventsToFile || false;

    if (this.logToFile) {
      this.initializeLogFile();
    }
  }

  /**
   * Initialize log file for this stream
   */
  initializeLogFile() {
    const logsDir = path.join(__dirname, '../../logs/events');
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    this.logFile = path.join(logsDir, `stream_${this.streamId}_${timestamp}.log`);

    this.writeToFile(`Stream Event Log Started: ${new Date().toISOString()}\n`);
    this.writeToFile(`Stream ID: ${this.streamId}\n`);
    this.writeToFile(`Call SID: ${this.callSid || 'N/A'}\n`);
    this.writeToFile('═'.repeat(80) + '\n\n');
  }

  /**
   * Write to log file
   */
  writeToFile(content) {
    if (this.logFile) {
      fs.appendFileSync(this.logFile, content);
    }
  }

  /**
   * Log WebSocket connection event
   */
  logConnection(data) {
    const event = {
      type: 'CONNECTION',
      timestamp: Date.now(),
      data: {
        clientIp: data.clientIp,
        userAgent: data.userAgent,
        sampleRate: data.sampleRate,
        customParams: data.customParams,
        authenticated: data.authenticated
      }
    };

    this._logEvent(event);
    this.logger.info('━━━ CONNECTION ESTABLISHED ━━━');
    this.logger.info(`  Client IP: ${data.clientIp}`);
    this.logger.info(`  Sample Rate: ${data.sampleRate} Hz`);
    if (data.customParams && Object.keys(data.customParams).length > 0) {
      this.logger.info('  Custom Params:', data.customParams);
    }
  }

  /**
   * Log stream start event
   */
  logStreamStart(streamInfo) {
    this.callSid = streamInfo.call_sid;

    const event = {
      type: 'STREAM_START',
      timestamp: Date.now(),
      data: {
        callSid: streamInfo.call_sid,
        accountSid: streamInfo.account_sid,
        from: streamInfo.from,
        to: streamInfo.to,
        mediaFormat: streamInfo.media_format,
        customParameters: streamInfo.custom_parameters
      }
    };

    this._logEvent(event);
    this.logger.info('━━━ STREAM STARTED ━━━');
    this.logger.info(`  Call SID: ${streamInfo.call_sid}`);
    this.logger.info(`  From: ${streamInfo.from} → To: ${streamInfo.to}`);
    this.logger.info(`  Encoding: ${streamInfo.media_format?.encoding}`);
    this.logger.info(`  Sample Rate: ${streamInfo.media_format?.sample_rate} Hz`);
    this.logger.info(`  Bit Rate: ${streamInfo.media_format?.bit_rate} bit`);

    if (streamInfo.custom_parameters) {
      this.logger.info('  Custom Parameters:', streamInfo.custom_parameters);
    }
  }

  /**
   * Log media event with statistics
   */
  logMedia(mediaData, stats = {}) {
    const event = {
      type: 'MEDIA',
      timestamp: Date.now(),
      data: {
        chunk: mediaData.chunk,
        timestamp: mediaData.timestamp,
        audioSize: mediaData.audioBuffer?.length || 0,
        duration: mediaData.duration,
        sequenceNumber: mediaData.sequenceNumber,
        stats
      }
    };

    this._logEvent(event);

    // Only log every Nth chunk to avoid spam
    if (mediaData.chunk % 100 === 0 || config.logging.level === 'debug') {
      this.logger.debug(`📦 Media Chunk #${mediaData.chunk}`, {
        timestamp: `${mediaData.timestamp}ms`,
        size: `${mediaData.audioBuffer?.length || 0} bytes`,
        duration: `${mediaData.duration?.toFixed(1)}ms`,
        totalChunks: stats.totalChunks || mediaData.chunk
      });
    }
  }

  /**
   * Log outgoing media event
   */
  logOutgoingMedia(audioBuffer, timestamp, chunkNumber) {
    const event = {
      type: 'MEDIA_SENT',
      timestamp: Date.now(),
      data: {
        chunk: chunkNumber,
        timestamp: timestamp,
        audioSize: audioBuffer.length,
        isValid: audioBuffer.length % 320 === 0
      }
    };

    this._logEvent(event);

    if (chunkNumber % 50 === 0 || config.logging.level === 'debug') {
      this.logger.debug(`📤 Sent Media Chunk #${chunkNumber}`, {
        timestamp: `${timestamp}ms`,
        size: `${audioBuffer.length} bytes`,
        valid: audioBuffer.length % 320 === 0 ? '✓' : '✗ (not multiple of 320)'
      });
    }
  }

  /**
   * Log DTMF event
   */
  logDTMF(dtmfData) {
    const event = {
      type: 'DTMF',
      timestamp: Date.now(),
      data: {
        digit: dtmfData.digit,
        duration: dtmfData.duration,
        sequenceNumber: dtmfData.sequenceNumber
      }
    };

    this._logEvent(event);
    this.logger.info('🔢 DTMF Detected', {
      digit: dtmfData.digit,
      duration: `${dtmfData.duration}ms`
    });
  }

  /**
   * Log mark event
   */
  logMark(markData, context = null) {
    const event = {
      type: 'MARK',
      timestamp: Date.now(),
      data: {
        name: markData.name,
        sequenceNumber: markData.sequenceNumber,
        context
      }
    };

    this._logEvent(event);
    this.logger.debug(`🏁 Mark Event: ${markData.name}`, context ? { context } : undefined);
  }

  /**
   * Log clear event
   */
  logClear(reason = null) {
    const event = {
      type: 'CLEAR',
      timestamp: Date.now(),
      data: { reason }
    };

    this._logEvent(event);
    this.logger.info('🧹 Clear Event - Audio queue cleared', reason ? { reason } : undefined);
  }

  /**
   * Log stream stop event
   */
  logStreamStop(stopData) {
    const event = {
      type: 'STREAM_STOP',
      timestamp: Date.now(),
      data: {
        callSid: stopData.callSid,
        accountSid: stopData.accountSid,
        reason: stopData.reason,
        totalChunks: stopData.totalChunks,
        duration: stopData.duration
      }
    };

    this._logEvent(event);
    this.logger.info('━━━ STREAM STOPPED ━━━');
    this.logger.info(`  Call SID: ${stopData.callSid}`);
    this.logger.info(`  Reason: ${stopData.reason}`);
    this.logger.info(`  Total Chunks: ${stopData.totalChunks}`);
    this.logger.info(`  Duration: ${(stopData.duration / 1000).toFixed(2)}s`);
  }

  /**
   * Log connection close event
   */
  logDisconnection(code, reason) {
    const event = {
      type: 'DISCONNECTION',
      timestamp: Date.now(),
      data: {
        code,
        reason: reason || 'No reason provided',
        totalDuration: Date.now() - this.startTime
      }
    };

    this._logEvent(event);
    this.logger.info('━━━ CONNECTION CLOSED ━━━');
    this.logger.info(`  Code: ${code}`);
    this.logger.info(`  Reason: ${reason || 'No reason provided'}`);
    this.logger.info(`  Total Duration: ${((Date.now() - this.startTime) / 1000).toFixed(2)}s`);

    this.generateSummary();
  }

  /**
   * Log error event
   */
  logError(error, context = {}) {
    const event = {
      type: 'ERROR',
      timestamp: Date.now(),
      data: {
        message: error.message,
        stack: error.stack,
        context
      }
    };

    this._logEvent(event);
    this.logger.error(`❌ Error: ${error.message}`, {
      context,
      stack: config.logging.level === 'debug' ? error.stack : undefined
    });
  }

  /**
   * Log custom bot event
   */
  logBotEvent(eventType, data) {
    const event = {
      type: `BOT_${eventType.toUpperCase()}`,
      timestamp: Date.now(),
      data
    };

    this._logEvent(event);
    this.logger.info(`🤖 Bot Event: ${eventType}`, data);
  }

  /**
   * Log state change
   */
  logStateChange(fromState, toState, reason = null) {
    const event = {
      type: 'STATE_CHANGE',
      timestamp: Date.now(),
      data: {
        from: fromState,
        to: toState,
        reason
      }
    };

    this._logEvent(event);
    this.logger.info(`🔄 State Change: ${fromState} → ${toState}`, reason ? { reason } : undefined);
  }

  /**
   * Internal method to log event
   */
  _logEvent(event) {
    this.events.push(event);

    if (this.logToFile) {
      const logLine = `[${new Date(event.timestamp).toISOString()}] ${event.type}\n`;
      const dataLine = `  ${JSON.stringify(event.data, null, 2)}\n\n`;
      this.writeToFile(logLine + dataLine);
    }
  }

  /**
   * Generate and log session summary
   */
  generateSummary() {
    const duration = Date.now() - this.startTime;
    const eventCounts = {};

    this.events.forEach(event => {
      eventCounts[event.type] = (eventCounts[event.type] || 0) + 1;
    });

    this.logger.info('━━━ SESSION SUMMARY ━━━');
    this.logger.info(`  Stream ID: ${this.streamId}`);
    this.logger.info(`  Call SID: ${this.callSid || 'N/A'}`);
    this.logger.info(`  Total Duration: ${(duration / 1000).toFixed(2)}s`);
    this.logger.info(`  Total Events: ${this.events.length}`);
    this.logger.info('  Event Breakdown:');

    Object.entries(eventCounts).forEach(([type, count]) => {
      this.logger.info(`    ${type}: ${count}`);
    });

    if (this.logToFile) {
      this.writeToFile('\n' + '═'.repeat(80) + '\n');
      this.writeToFile('SESSION SUMMARY\n');
      this.writeToFile('═'.repeat(80) + '\n');
      this.writeToFile(`Stream ID: ${this.streamId}\n`);
      this.writeToFile(`Call SID: ${this.callSid || 'N/A'}\n`);
      this.writeToFile(`Total Duration: ${(duration / 1000).toFixed(2)}s\n`);
      this.writeToFile(`Total Events: ${this.events.length}\n`);
      this.writeToFile('\nEvent Breakdown:\n');
      Object.entries(eventCounts).forEach(([type, count]) => {
        this.writeToFile(`  ${type}: ${count}\n`);
      });

      this.logger.info(`  Event log saved: ${this.logFile}`);
    }
  }

  /**
   * Get all events
   */
  getEvents() {
    return this.events;
  }

  /**
   * Get events by type
   */
  getEventsByType(type) {
    return this.events.filter(event => event.type === type);
  }

  /**
   * Get event statistics
   */
  getStatistics() {
    const stats = {
      totalEvents: this.events.length,
      duration: Date.now() - this.startTime,
      eventCounts: {},
      mediaStats: {
        received: 0,
        sent: 0,
        totalBytes: 0
      }
    };

    this.events.forEach(event => {
      stats.eventCounts[event.type] = (stats.eventCounts[event.type] || 0) + 1;

      if (event.type === 'MEDIA') {
        stats.mediaStats.received++;
        stats.mediaStats.totalBytes += event.data.audioSize || 0;
      } else if (event.type === 'MEDIA_SENT') {
        stats.mediaStats.sent++;
      }
    });

    return stats;
  }
}

module.exports = EventLogger;

