/**
 * Jest Test Setup
 * Runs before each test file
 */

// Set test environment
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = 'error'; // Quiet logs during tests

// Mock console to reduce noise (optional)
// global.console = {
//   ...console,
//   log: jest.fn(),
//   debug: jest.fn(),
//   info: jest.fn(),
//   warn: jest.fn()
// };

// Increase timeout for integration tests
jest.setTimeout(10000);

// Global test utilities
global.testUtils = {
  /**
   * Wait for a specified time
   */
  wait: (ms) => new Promise(resolve => setTimeout(resolve, ms)),
  
  /**
   * Create mock WebSocket
   */
  createMockWebSocket: () => ({
    readyState: 1, // OPEN
    send: jest.fn(),
    close: jest.fn(),
    on: jest.fn(),
    OPEN: 1
  }),
  
  /**
   * Create mock Exotel start event
   */
  createMockStartEvent: (overrides = {}) => ({
    event: 'start',
    sequence_number: '1',
    start: {
      call_sid: 'test-call-123',
      account_sid: 'test-account-456',
      from: '+1234567890',
      to: '+0987654321',
      media_format: {
        encoding: 'linear16',
        sample_rate: 8000,
        bit_rate: 16
      },
      ...overrides
    }
  }),
  
  /**
   * Create mock media event
   */
  createMockMediaEvent: (payload = '') => ({
    event: 'media',
    sequence_number: '2',
    media: {
      chunk: '1',
      timestamp: Date.now().toString(),
      payload: payload || Buffer.alloc(320).toString('base64')
    }
  }),
  
  /**
   * Create mock audio buffer
   */
  createMockAudioBuffer: (sizeBytes = 320) => {
    const buffer = Buffer.alloc(sizeBytes);
    // Fill with random audio-like data
    for (let i = 0; i < sizeBytes; i += 2) {
      buffer.writeInt16LE(Math.floor(Math.random() * 1000) - 500, i);
    }
    return buffer;
  }
};

// Cleanup after all tests
afterAll(async () => {
  // Allow pending operations to complete
  await new Promise(resolve => setTimeout(resolve, 100));
});

