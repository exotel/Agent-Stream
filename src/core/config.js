require('dotenv').config();

module.exports = {
  server: {
    port: process.env.PORT || 5001,
    host: process.env.HOST || '0.0.0.0',
    wsPath: process.env.WS_PATH || '/media'
  },

  ssl: {
    enabled: process.env.USE_SSL === 'true',
    certPath: process.env.SSL_CERT_PATH,
    keyPath: process.env.SSL_KEY_PATH
  },

  auth: {
    apiKey: process.env.API_KEY,
    apiToken: process.env.API_TOKEN,
    enabled: !!(process.env.API_KEY && process.env.API_TOKEN)
  },

  logging: {
    level: process.env.LOG_LEVEL || 'info',
    logMediaPayloads: process.env.LOG_MEDIA_PAYLOADS === 'true',
    logEventsToFile: process.env.LOG_EVENTS_TO_FILE === 'true',
    logHttpRequests: process.env.LOG_HTTP_REQUESTS !== 'false' // Default true
  },

  audio: {
    defaultSampleRate: parseInt(process.env.DEFAULT_SAMPLE_RATE) || 8000,
    supportedSampleRates: (process.env.SUPPORTED_SAMPLE_RATES || '8000,16000,24000')
      .split(',')
      .map(rate => parseInt(rate.trim()))
  },

  // Chunk size constraints for bidirectional streaming
  chunkSize: {
    min: 3200,  // 100ms data (minimum)
    max: 100000, // Maximum chunk size
    alignment: 320 // Chunk size must be multiple of this
  },

  // Noise cancellation configuration
  noiseCancellation: {
    enabled: process.env.ENABLE_NOISE_CANCELLATION === 'true',
    processorType: process.env.NOISE_PROCESSOR_TYPE || 'rnnoise', // rnnoise, spectral
    mode: process.env.NOISE_PROCESSING_MODE || 'both', // both, incoming_only, outgoing_only, disabled
    maxLatencyMs: parseInt(process.env.MAX_PROCESSING_LATENCY_MS) || 30,
    enableStats: process.env.ENABLE_PROCESSING_STATS === 'true'
  }
};

