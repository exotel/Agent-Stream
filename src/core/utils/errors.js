/**
 * Error Handling Utilities
 * Enterprise-grade error handling with retry logic and circuit breaker
 */

const StructuredLogger = require('./structured-logger');
const logger = new StructuredLogger('ERROR-HANDLER');

// ═══════════════════════════════════════════════════════════════════════════════
// Custom Error Classes
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Base application error
 */
class AppError extends Error {
  constructor(message, code = 'INTERNAL_ERROR', statusCode = 500, isOperational = true) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.timestamp = new Date().toISOString();
    Error.captureStackTrace(this, this.constructor);
  }

  toJSON() {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      statusCode: this.statusCode,
      timestamp: this.timestamp
    };
  }
}

/**
 * Validation error
 */
class ValidationError extends AppError {
  constructor(message, field = null) {
    super(message, 'VALIDATION_ERROR', 400);
    this.name = 'ValidationError';
    this.field = field;
  }
}

/**
 * External service error
 */
class ExternalServiceError extends AppError {
  constructor(service, message, originalError = null) {
    super(`${service}: ${message}`, 'EXTERNAL_SERVICE_ERROR', 502);
    this.name = 'ExternalServiceError';
    this.service = service;
    this.originalError = originalError;
  }
}

/**
 * Rate limit error
 */
class RateLimitError extends AppError {
  constructor(service, retryAfter = null) {
    super(`Rate limit exceeded for ${service}`, 'RATE_LIMIT_ERROR', 429);
    this.name = 'RateLimitError';
    this.service = service;
    this.retryAfter = retryAfter;
  }
}

/**
 * Circuit breaker open error
 */
class CircuitBreakerError extends AppError {
  constructor(service) {
    super(`Circuit breaker is open for ${service}`, 'CIRCUIT_BREAKER_OPEN', 503);
    this.name = 'CircuitBreakerError';
    this.service = service;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Retry Utility
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Retry with exponential backoff
 */
class RetryHandler {
  constructor(options = {}) {
    this.options = {
      maxRetries: options.maxRetries || 3,
      baseDelayMs: options.baseDelayMs || 1000,
      maxDelayMs: options.maxDelayMs || 30000,
      backoffMultiplier: options.backoffMultiplier || 2,
      jitter: options.jitter !== false,
      retryCondition: options.retryCondition || this.defaultRetryCondition
    };
  }

  /**
   * Default retry condition - retry on network errors and 5xx responses
   */
  defaultRetryCondition(error) {
    // Network errors
    if (error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT' ||
        error.code === 'ECONNREFUSED') {
      return true;
    }

    // Rate limit with retry-after
    if (error.statusCode === 429) {
      return true;
    }

    // Server errors
    if (error.statusCode >= 500 && error.statusCode < 600) {
      return true;
    }

    return false;
  }

  /**
   * Calculate delay with exponential backoff and jitter
   */
  calculateDelay(attempt) {
    let delay = this.options.baseDelayMs * Math.pow(this.options.backoffMultiplier, attempt);
    delay = Math.min(delay, this.options.maxDelayMs);

    if (this.options.jitter) {
      // Add 0-25% jitter
      delay = delay * (1 + Math.random() * 0.25);
    }

    return Math.floor(delay);
  }

  /**
   * Execute function with retry logic
   */
  async execute(fn, context = 'operation') {
    let lastError;

    for (let attempt = 0; attempt <= this.options.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;

        const shouldRetry = attempt < this.options.maxRetries &&
                           this.options.retryCondition(error);

        if (!shouldRetry) {
          throw error;
        }

        const delay = this.calculateDelay(attempt);

        logger.warn(`Retry attempt ${attempt + 1}/${this.options.maxRetries} for ${context}`, {
          error: error.message,
          delay: `${delay}ms`,
          attempt: attempt + 1
        });

        await this.sleep(delay);
      }
    }

    throw lastError;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Circuit Breaker
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Circuit breaker pattern implementation
 */
class CircuitBreaker {
  constructor(options = {}) {
    this.options = {
      failureThreshold: options.failureThreshold || 5,
      successThreshold: options.successThreshold || 2,
      timeout: options.timeout || 30000,
      resetTimeout: options.resetTimeout || 60000,
      ...options
    };

    this.state = 'closed'; // closed, open, half-open
    this.failures = 0;
    this.successes = 0;
    this.lastFailureTime = null;
    this.nextAttemptTime = null;
  }

  /**
   * Check if circuit allows requests
   */
  canExecute() {
    if (this.state === 'closed') {
      return true;
    }

    if (this.state === 'open') {
      // Check if we should try half-open
      if (Date.now() >= this.nextAttemptTime) {
        this.state = 'half-open';
        this.successes = 0;
        logger.info('Circuit breaker entering half-open state');
        return true;
      }
      return false;
    }

    // half-open: allow limited requests
    return true;
  }

  /**
   * Record successful execution
   */
  recordSuccess() {
    if (this.state === 'half-open') {
      this.successes++;
      if (this.successes >= this.options.successThreshold) {
        this.state = 'closed';
        this.failures = 0;
        logger.info('Circuit breaker closed after successful recovery');
      }
    } else if (this.state === 'closed') {
      this.failures = 0;
    }
  }

  /**
   * Record failed execution
   */
  recordFailure() {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.state === 'half-open') {
      this.state = 'open';
      this.nextAttemptTime = Date.now() + this.options.resetTimeout;
      logger.warn('Circuit breaker opened after failure in half-open state');
    } else if (this.state === 'closed' && this.failures >= this.options.failureThreshold) {
      this.state = 'open';
      this.nextAttemptTime = Date.now() + this.options.resetTimeout;
      logger.warn('Circuit breaker opened after reaching failure threshold', {
        failures: this.failures,
        threshold: this.options.failureThreshold
      });
    }
  }

  /**
   * Execute function with circuit breaker protection
   */
  async execute(fn, serviceName = 'service') {
    if (!this.canExecute()) {
      throw new CircuitBreakerError(serviceName);
    }

    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  /**
   * Get current state
   */
  getState() {
    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      lastFailureTime: this.lastFailureTime,
      nextAttemptTime: this.nextAttemptTime
    };
  }

  /**
   * Force reset the circuit breaker
   */
  reset() {
    this.state = 'closed';
    this.failures = 0;
    this.successes = 0;
    this.lastFailureTime = null;
    this.nextAttemptTime = null;
    logger.info('Circuit breaker manually reset');
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Error Handler Middleware
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Express error handling middleware
 */
function errorMiddleware(err, req, res, next) {
  // Log the error
  logger.error('Request error', {
    error: err,
    method: req.method,
    url: req.url,
    correlationId: req.correlationId
  });

  // Determine status code
  const statusCode = err.statusCode || err.status || 500;

  // Build error response
  const errorResponse = {
    error: {
      code: err.code || 'INTERNAL_ERROR',
      message: err.isOperational ? err.message : 'An unexpected error occurred',
      ...(process.env.NODE_ENV !== 'production' && { stack: err.stack })
    },
    correlationId: req.correlationId,
    timestamp: new Date().toISOString()
  };

  res.status(statusCode).json(errorResponse);
}

/**
 * Async error wrapper for express routes
 */
function asyncHandler(fn) {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Exports
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = {
  // Error classes
  AppError,
  ValidationError,
  ExternalServiceError,
  RateLimitError,
  CircuitBreakerError,

  // Utilities
  RetryHandler,
  CircuitBreaker,

  // Middleware
  errorMiddleware,
  asyncHandler
};

