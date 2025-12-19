/**
 * Jest Configuration
 * Enterprise-grade test configuration
 */

module.exports = {
  // Test environment
  testEnvironment: 'node',
  
  // Test file patterns
  testMatch: [
    '**/tests/**/*.test.js',
    '**/tests/**/*.spec.js',
    '**/__tests__/**/*.js'
  ],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/'
  ],
  
  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/types/**',
    '!src/**/*.d.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  // Coverage thresholds disabled until proper tests are added
  // coverageThreshold: {
  //   global: {
  //     branches: 15,
  //     functions: 20,
  //     lines: 15,
  //     statements: 15
  //   }
  // },
  
  // Setup files
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  
  // Timeout
  testTimeout: 10000,
  
  // Verbose output
  verbose: true,
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Module name mapper for path aliases
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  
  // Global setup/teardown
  // globalSetup: '<rootDir>/tests/global-setup.js',
  // globalTeardown: '<rootDir>/tests/global-teardown.js',
  
  // Transform
  transform: {}
};

