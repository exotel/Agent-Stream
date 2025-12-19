/**
 * Audio Resampler Unit Tests
 */

const AudioResampler = require('../../src/core/utils/audioResampler');

describe('AudioResampler', () => {
  describe('resample', () => {
    it('should return same buffer when rates match', () => {
      const input = global.testUtils.createMockAudioBuffer(320);
      
      const result = AudioResampler.resample(input, 8000, 8000);
      
      expect(result).toBe(input); // Same reference
    });

    it('should upsample from 8kHz to 16kHz', () => {
      const input = global.testUtils.createMockAudioBuffer(320);
      
      const result = AudioResampler.resample(input, 8000, 16000);
      
      // Output should be twice the size
      expect(result.length).toBe(640);
      expect(Buffer.isBuffer(result)).toBe(true);
    });

    it('should upsample from 8kHz to 24kHz', () => {
      const input = global.testUtils.createMockAudioBuffer(320);
      
      const result = AudioResampler.resample(input, 8000, 24000);
      
      // Output should be 3x the size
      expect(result.length).toBe(960);
    });

    it('should downsample from 24kHz to 8kHz', () => {
      const input = global.testUtils.createMockAudioBuffer(960);
      
      const result = AudioResampler.resample(input, 24000, 8000);
      
      // Output should be 1/3 the size
      expect(result.length).toBe(320);
    });

    it('should downsample from 16kHz to 8kHz', () => {
      const input = global.testUtils.createMockAudioBuffer(640);
      
      const result = AudioResampler.resample(input, 16000, 8000);
      
      // Output should be half the size
      expect(result.length).toBe(320);
    });
  });

  describe('convenience methods', () => {
    it('to8kHz should resample correctly', () => {
      const input = global.testUtils.createMockAudioBuffer(640);
      
      const result = AudioResampler.to8kHz(input, 16000);
      
      expect(result.length).toBe(320);
    });

    it('to16kHz should resample correctly', () => {
      const input = global.testUtils.createMockAudioBuffer(320);
      
      const result = AudioResampler.to16kHz(input, 8000);
      
      expect(result.length).toBe(640);
    });

    it('to24kHz should resample correctly', () => {
      const input = global.testUtils.createMockAudioBuffer(320);
      
      const result = AudioResampler.to24kHz(input, 8000);
      
      expect(result.length).toBe(960);
    });
  });

  describe('utility methods', () => {
    it('getSampleCount should return correct count', () => {
      const buffer = Buffer.alloc(320);
      
      const count = AudioResampler.getSampleCount(buffer);
      
      expect(count).toBe(160); // 320 bytes / 2 bytes per sample
    });

    it('getDuration should return correct duration', () => {
      const buffer = Buffer.alloc(1600); // 800 samples
      
      const duration = AudioResampler.getDuration(buffer, 8000);
      
      expect(duration).toBe(100); // 800 samples / 8000 samples per sec = 0.1 sec = 100ms
    });

    it('isValidPCM should validate buffer', () => {
      expect(AudioResampler.isValidPCM(Buffer.alloc(320))).toBe(true);
      expect(AudioResampler.isValidPCM(Buffer.alloc(0))).toBe(false);
      expect(AudioResampler.isValidPCM(Buffer.alloc(321))).toBe(false); // Odd
      expect(AudioResampler.isValidPCM('not a buffer')).toBe(false);
      expect(AudioResampler.isValidPCM(null)).toBe(false);
    });
  });
});

