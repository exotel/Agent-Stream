/**
 * Exotel Voice AI - Main Entry Point
 *
 * This file exports the core framework components for building voice bots.
 *
 * @example
 * const { createServer, MessageHandler, MessageSender } = require('./src');
 */

// Core Framework
const server = require('./core/server');
const config = require('./core/config');

// Handlers
const MessageHandler = require('./core/handlers/messageHandler');
const MessageSender = require('./core/handlers/messageSender');

// Utilities
const logger = require('./core/utils/logger');
const audioResampler = require('./core/utils/audioResampler');
const BotUtils = require('./core/utils/botUtils');

// Audio Processing
const AudioProcessor = require('./core/audio/audioProcessor');

module.exports = {
  // Server
  createServer: server.createServer,

  // Configuration
  config,

  // Handlers
  MessageHandler,
  MessageSender,

  // Utilities
  logger,
  audioResampler,
  BotUtils,

  // Audio
  AudioProcessor,

  // Version
  version: require('../package.json').version
};

