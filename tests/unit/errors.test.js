/**
 * Error Handling Utilities Tests
 */

const {
  AppError,
  ValidationError,
  ExternalServiceError,
  RetryHandler,
  CircuitBreaker
} = require('../../src/core/utils/errors');

describe('Error Classes', () => {
  describe('AppError', () => {
    it('should create error with correct properties', () => {
      const error = new AppError('Test error', 'TEST_ERROR', 400);
      
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('TEST_ERROR');
      expect(error.statusCode).toBe(400);
      expect(error.isOperational).toBe(true);
      expect(error.timestamp).toBeDefined();
    });

    it('should serialize to JSON correctly', () => {
      const error = new AppError('Test error', 'TEST_ERROR', 400);
      const json = error.toJSON();
      
      expect(json.message).toBe('Test error');
      expect(json.code).toBe('TEST_ERROR');
      expect(json.statusCode).toBe(400);
    });
  });

  describe('ValidationError', () => {
    it('should have correct status code', () => {
      const error = new ValidationError('Invalid input', 'email');
      
      expect(error.statusCode).toBe(400);
      expect(error.code).toBe('VALIDATION_ERROR');
      expect(error.field).toBe('email');
    });
  });

  describe('ExternalServiceError', () => {
    it('should include service name', () => {
      const error = new ExternalServiceError('OpenAI', 'Connection failed');
      
      expect(error.message).toBe('OpenAI: Connection failed');
      expect(error.statusCode).toBe(502);
      expect(error.service).toBe('OpenAI');
    });
  });
});

describe('RetryHandler', () => {
  describe('execute', () => {
    it('should return result on first success', async () => {
      const handler = new RetryHandler({ maxRetries: 3 });
      const fn = jest.fn().mockResolvedValue('success');
      
      const result = await handler.execute(fn);
      
      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure and eventually succeed', async () => {
      const handler = new RetryHandler({ 
        maxRetries: 3, 
        baseDelayMs: 10 
      });
      
      const fn = jest.fn()
        .mockRejectedValueOnce({ code: 'ECONNRESET' })
        .mockRejectedValueOnce({ code: 'ECONNRESET' })
        .mockResolvedValue('success');
      
      const result = await handler.execute(fn);
      
      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should throw after max retries exceeded', async () => {
      const handler = new RetryHandler({ 
        maxRetries: 2, 
        baseDelayMs: 10 
      });
      
      const error = { code: 'ECONNRESET', message: 'Connection reset' };
      const fn = jest.fn().mockRejectedValue(error);
      
      await expect(handler.execute(fn)).rejects.toEqual(error);
      expect(fn).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    it('should not retry non-retryable errors', async () => {
      const handler = new RetryHandler({ maxRetries: 3 });
      
      const error = { statusCode: 400, message: 'Bad request' };
      const fn = jest.fn().mockRejectedValue(error);
      
      await expect(handler.execute(fn)).rejects.toEqual(error);
      expect(fn).toHaveBeenCalledTimes(1); // No retries
    });
  });

  describe('calculateDelay', () => {
    it('should calculate exponential delay', () => {
      const handler = new RetryHandler({ 
        baseDelayMs: 1000, 
        backoffMultiplier: 2,
        jitter: false 
      });
      
      expect(handler.calculateDelay(0)).toBe(1000);
      expect(handler.calculateDelay(1)).toBe(2000);
      expect(handler.calculateDelay(2)).toBe(4000);
    });

    it('should cap delay at maxDelayMs', () => {
      const handler = new RetryHandler({ 
        baseDelayMs: 1000, 
        maxDelayMs: 5000,
        backoffMultiplier: 2,
        jitter: false 
      });
      
      expect(handler.calculateDelay(10)).toBe(5000);
    });
  });
});

describe('CircuitBreaker', () => {
  describe('execute', () => {
    it('should allow requests when closed', async () => {
      const breaker = new CircuitBreaker({ failureThreshold: 3 });
      const fn = jest.fn().mockResolvedValue('success');
      
      const result = await breaker.execute(fn);
      
      expect(result).toBe('success');
      expect(breaker.getState().state).toBe('closed');
    });

    it('should open after failure threshold', async () => {
      const breaker = new CircuitBreaker({ 
        failureThreshold: 3,
        resetTimeout: 1000
      });
      
      const fn = jest.fn().mockRejectedValue(new Error('fail'));
      
      // Trigger 3 failures
      for (let i = 0; i < 3; i++) {
        await expect(breaker.execute(fn)).rejects.toThrow('fail');
      }
      
      expect(breaker.getState().state).toBe('open');
    });

    it('should reject requests when open', async () => {
      const breaker = new CircuitBreaker({ 
        failureThreshold: 1,
        resetTimeout: 10000
      });
      
      // Trigger opening
      const failFn = jest.fn().mockRejectedValue(new Error('fail'));
      await expect(breaker.execute(failFn, 'test')).rejects.toThrow('fail');
      
      expect(breaker.getState().state).toBe('open');
      
      // Next call should be rejected with circuit breaker error
      const successFn = jest.fn().mockResolvedValue('success');
      await expect(breaker.execute(successFn, 'test'))
        .rejects.toThrow('Circuit breaker is open');
      
      // Success function should not have been called
      expect(successFn).not.toHaveBeenCalled();
    });
  });

  describe('reset', () => {
    it('should reset circuit breaker state', async () => {
      const breaker = new CircuitBreaker({ failureThreshold: 1 });
      
      // Trigger opening
      const fn = jest.fn().mockRejectedValue(new Error('fail'));
      await expect(breaker.execute(fn)).rejects.toThrow('fail');
      
      expect(breaker.getState().state).toBe('open');
      
      // Reset
      breaker.reset();
      
      expect(breaker.getState().state).toBe('closed');
      expect(breaker.getState().failures).toBe(0);
    });
  });
});

