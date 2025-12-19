const config = require('../config');

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

class Logger {
  constructor(context = 'APP') {
    this.context = context;
    this.level = LOG_LEVELS[config.logging.level] || LOG_LEVELS.info;
  }

  _log(level, message, ...args) {
    if (LOG_LEVELS[level] <= this.level) {
      const timestamp = new Date().toISOString();
      const prefix = `[${timestamp}] [${level.toUpperCase()}] [${this.context}]`;
      console.log(prefix, message, ...args);
    }
  }

  error(message, ...args) {
    this._log('error', message, ...args);
  }

  warn(message, ...args) {
    this._log('warn', message, ...args);
  }

  info(message, ...args) {
    this._log('info', message, ...args);
  }

  debug(message, ...args) {
    this._log('debug', message, ...args);
  }
}

module.exports = Logger;

