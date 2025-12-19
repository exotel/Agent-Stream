/**
 * Exotel Voice Bot Framework
 * 
 * Usage:
 *   const { ExotelWSSServer, ExotelApi, AudioResampler, Logger } = require('exotel-voice-bot');
 */

const ExotelWSSServer = require('./src/server');
const ExotelApi = require('./src/utils/exotelApi');
const AudioResampler = require('./src/utils/audioResampler');
const AudioUtilsBase = require('./src/utils/audio');
const Logger = require('./src/utils/logger');
const MessageSender = require('./src/handlers/messageSender');
const MessageHandler = require('./src/handlers/messageHandler');
const config = require('./src/config');
const { SessionState, AudioUtils, BargeInHandler, EXOTEL_CONSTANTS } = require('./src/utils/botUtils');

module.exports = {
  // Core
  ExotelWSSServer,
  ExotelApi,
  
  // Utilities
  AudioResampler,
  AudioUtils,
  AudioUtilsBase,
  Logger,
  
  // Bot utilities (learnings consolidated)
  SessionState,
  BargeInHandler,
  EXOTEL_CONSTANTS,
  
  // Handlers
  MessageSender,
  MessageHandler,
  
  // Configuration
  config,
  
  // Convenience function to create a bot
  createBot: (options = {}) => {
    return new ExotelWSSServer(options);
  },
  
  // Convenience function to create Exotel API client
  createExotelClient: (options = {}) => {
    return new ExotelApi(options);
  }
};

