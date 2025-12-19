const Logger = require('../utils/logger');
const logger = new Logger('HTTP');

/**
 * Request logging middleware
 * Logs all HTTP requests with detailed information
 */
class RequestLogger {
  /**
   * Express middleware for logging HTTP requests
   */
  static middleware() {
    return (req, res, next) => {
      const startTime = Date.now();
      const requestId = req.headers['x-request-id'] || `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Attach request ID to request object
      req.requestId = requestId;

      // Log incoming request
      logger.info(`→ ${req.method} ${req.url}`, {
        requestId,
        ip: req.ip || req.socket.remoteAddress,
        userAgent: req.headers['user-agent'],
        query: Object.keys(req.query).length > 0 ? req.query : undefined
      });

      // Log request body for POST/PUT (sanitize sensitive data)
      if (['POST', 'PUT', 'PATCH'].includes(req.method) && req.body) {
        const sanitizedBody = this.sanitizeBody(req.body);
        logger.debug('  Request Body:', sanitizedBody);
      }

      // Capture response
      const originalSend = res.send;
      res.send = function(data) {
        res.send = originalSend;

        const duration = Date.now() - startTime;
        const statusCode = res.statusCode;
        const level = statusCode >= 500 ? 'error' : statusCode >= 400 ? 'warn' : 'info';

        logger[level](`← ${req.method} ${req.url} ${statusCode} ${duration}ms`, {
          requestId,
          statusCode,
          duration,
          contentLength: res.get('content-length')
        });

        return originalSend.call(this, data);
      };

      next();
    };
  }

  /**
   * Sanitize request body (remove sensitive fields)
   */
  static sanitizeBody(body) {
    const sensitiveFields = ['password', 'token', 'api_key', 'secret', 'authorization'];
    const sanitized = { ...body };

    for (const field of sensitiveFields) {
      if (sanitized[field]) {
        sanitized[field] = '***REDACTED***';
      }
    }

    return sanitized;
  }

  /**
   * Log error with full context
   */
  static logError(req, error) {
    logger.error(`Error processing ${req.method} ${req.url}:`, {
      requestId: req.requestId,
      error: error.message,
      stack: error.stack,
      ip: req.ip || req.socket.remoteAddress
    });
  }
}

module.exports = RequestLogger;

