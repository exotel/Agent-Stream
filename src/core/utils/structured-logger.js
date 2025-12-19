/**
 * Structured Logger with Correlation IDs
 * Enterprise-grade logging for production environments
 *
 * Features:
 * - JSON structured output for log aggregation (ELK, Datadog, etc.)
 * - Correlation ID tracking across requests
 * - Log levels with filtering
 * - Context enrichment
 * - Error serialization
 */

const { v4: uuidv4 } = require('uuid');
const config = require('../config');

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

// Async local storage for correlation ID tracking
const { AsyncLocalStorage } = require('async_hooks');
const asyncLocalStorage = new AsyncLocalStorage();

class StructuredLogger {
  constructor(context = 'APP', options = {}) {
    this.context = context;
    this.level = LOG_LEVELS[config.logging?.level] || LOG_LEVELS.info;
    this.jsonFormat = process.env.LOG_FORMAT === 'json' || process.env.NODE_ENV === 'production';
    this.options = {
      includeTimestamp: true,
      includeHostname: process.env.NODE_ENV === 'production',
      ...options
    };

    // Get hostname for distributed tracing
    this.hostname = process.env.HOSTNAME || require('os').hostname();
  }

  /**
   * Get current correlation ID from async context
   */
  static getCorrelationId() {
    const store = asyncLocalStorage.getStore();
    return store?.correlationId;
  }

  /**
   * Set correlation ID for the current async context
   */
  static setCorrelationId(correlationId) {
    const store = asyncLocalStorage.getStore();
    if (store) {
      store.correlationId = correlationId;
    }
  }

  /**
   * Run function with correlation ID context
   */
  static runWithCorrelationId(correlationId, fn) {
    return asyncLocalStorage.run({ correlationId }, fn);
  }

  /**
   * Generate new correlation ID
   */
  static generateCorrelationId() {
    return uuidv4();
  }

  /**
   * Express middleware for correlation ID
   */
  static correlationMiddleware() {
    return (req, res, next) => {
      const correlationId = req.headers['x-correlation-id'] ||
                           req.headers['x-request-id'] ||
                           StructuredLogger.generateCorrelationId();

      // Set response header
      res.setHeader('x-correlation-id', correlationId);

      // Run in async context
      asyncLocalStorage.run({ correlationId }, () => {
        req.correlationId = correlationId;
        next();
      });
    };
  }

  /**
   * Create log entry
   */
  _createLogEntry(level, message, data = {}) {
    const correlationId = StructuredLogger.getCorrelationId();

    const entry = {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      context: this.context,
      message,
      ...(correlationId && { correlationId }),
      ...(this.options.includeHostname && { hostname: this.hostname }),
      ...(Object.keys(data).length > 0 && { data })
    };

    return entry;
  }

  /**
   * Format error for logging
   */
  _formatError(error) {
    if (!error) return undefined;

    return {
      name: error.name,
      message: error.message,
      code: error.code,
      statusCode: error.statusCode,
      stack: process.env.NODE_ENV !== 'production' ? error.stack : undefined,
      ...(error.context && { context: error.context })
    };
  }

  /**
   * Output log entry
   */
  _output(level, entry) {
    if (LOG_LEVELS[level] > this.level) return;

    if (this.jsonFormat) {
      console.log(JSON.stringify(entry));
    } else {
      const prefix = `[${entry.timestamp}] [${entry.level}] [${entry.context}]`;
      const correlationPart = entry.correlationId ? ` [${entry.correlationId.substring(0, 8)}]` : '';

      if (entry.data && Object.keys(entry.data).length > 0) {
        console.log(`${prefix}${correlationPart}`, entry.message, entry.data);
      } else {
        console.log(`${prefix}${correlationPart}`, entry.message);
      }
    }
  }

  /**
   * Log methods
   */
  error(message, data = {}) {
    const entry = this._createLogEntry('error', message, data);
    if (data.error || data instanceof Error) {
      entry.error = this._formatError(data.error || data);
    }
    this._output('error', entry);
  }

  warn(message, data = {}) {
    const entry = this._createLogEntry('warn', message, data);
    this._output('warn', entry);
  }

  info(message, data = {}) {
    const entry = this._createLogEntry('info', message, data);
    this._output('info', entry);
  }

  debug(message, data = {}) {
    const entry = this._createLogEntry('debug', message, data);
    this._output('debug', entry);
  }

  /**
   * Create child logger with additional context
   */
  child(additionalContext) {
    const childLogger = new StructuredLogger(`${this.context}:${additionalContext}`, this.options);
    childLogger.level = this.level;
    childLogger.jsonFormat = this.jsonFormat;
    return childLogger;
  }

  /**
   * Log HTTP request (for middleware)
   */
  logRequest(req, res, duration) {
    const entry = this._createLogEntry('info', 'HTTP Request', {
      method: req.method,
      url: req.url,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      userAgent: req.headers['user-agent'],
      ip: req.ip || req.socket?.remoteAddress
    });
    this._output('info', entry);
  }

  /**
   * Log WebSocket event
   */
  logWsEvent(eventType, streamId, data = {}) {
    const entry = this._createLogEntry('info', `WebSocket ${eventType}`, {
      streamId: streamId?.substring(0, 8),
      eventType,
      ...data
    });
    this._output('info', entry);
  }

  /**
   * Log AI service call
   */
  logAICall(service, provider, duration, success, data = {}) {
    const level = success ? 'info' : 'error';
    const entry = this._createLogEntry(level, `AI Service Call: ${service}`, {
      service,
      provider,
      duration: `${duration}ms`,
      success,
      ...data
    });
    this._output(level, entry);
  }
}

module.exports = StructuredLogger;

