/**
 * Basic Tests
 * Verifies core modules can be loaded
 */

describe('Module Loading', () => {
  test('src/core/config loads', () => {
    const config = require('../src/core/config');
    expect(config).toBeDefined();
    expect(config.server).toBeDefined();
    expect(config.server.port).toBeDefined();
  });

  test('src/core/utils/logger loads', () => {
    const logger = require('../src/core/utils/logger');
    expect(logger).toBeDefined();
  });

  test('src/core/utils/audioResampler loads', () => {
    const resampler = require('../src/core/utils/audioResampler');
    expect(resampler).toBeDefined();
  });

  test('src/core/utils/botUtils loads', () => {
    const botUtils = require('../src/core/utils/botUtils');
    expect(botUtils).toBeDefined();
    expect(botUtils.SessionState).toBeDefined();
  });
});

describe('BotUtils', () => {
  const botUtils = require('../src/core/utils/botUtils');

  test('BargeInHandler class exists', () => {
    expect(botUtils.BargeInHandler).toBeDefined();
  });

  test('SessionState class exists', () => {
    expect(botUtils.SessionState).toBeDefined();
  });

  test('AudioUtils has calculateAudioLevel', () => {
    expect(botUtils.AudioUtils).toBeDefined();
    const buffer = Buffer.alloc(100);
    const level = botUtils.AudioUtils.calculateAudioLevel(buffer);
    expect(typeof level).toBe('number');
    expect(level).toBe(0); // Silent buffer
  });

  test('EXOTEL_CONSTANTS exists', () => {
    expect(botUtils.EXOTEL_CONSTANTS).toBeDefined();
  });
});

describe('Config', () => {
  const config = require('../src/core/config');

  test('has server settings', () => {
    expect(config.server).toBeDefined();
    expect(config.server.port).toBeDefined();
  });

  test('has audio settings', () => {
    expect(config.audio).toBeDefined();
    expect(config.audio.defaultSampleRate).toBeDefined();
  });

  test('has logging settings', () => {
    expect(config.logging).toBeDefined();
  });
});

