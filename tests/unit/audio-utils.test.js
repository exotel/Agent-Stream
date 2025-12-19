/**
 * Audio Utilities Unit Tests
 */

const AudioUtils = require('../../src/core/utils/audio');

describe('AudioUtils', () => {
  describe('validateChunkSize', () => {
    it('should accept valid chunk size', () => {
      const result = AudioUtils.validateChunkSize(3200);
      expect(result.valid).toBe(true);
    });

    it('should reject chunk size below minimum', () => {
      const result = AudioUtils.validateChunkSize(100);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('below minimum');
    });

    it('should reject chunk size above maximum', () => {
      const result = AudioUtils.validateChunkSize(200000);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('exceeds maximum');
    });

    it('should reject chunk size not aligned to 320 bytes', () => {
      const result = AudioUtils.validateChunkSize(3250);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('not a multiple');
    });
  });

  describe('encodeAudio / decodeAudio', () => {
    it('should encode and decode audio correctly', () => {
      const originalBuffer = global.testUtils.createMockAudioBuffer(320);
      
      const encoded = AudioUtils.encodeAudio(originalBuffer);
      expect(typeof encoded).toBe('string');
      
      const decoded = AudioUtils.decodeAudio(encoded);
      expect(Buffer.isBuffer(decoded)).toBe(true);
      expect(decoded).toEqual(originalBuffer);
    });
  });

  describe('calculateDuration', () => {
    it('should calculate duration for 8kHz audio', () => {
      // 8000 samples/sec * 2 bytes/sample = 16000 bytes/sec
      // 1600 bytes = 100ms
      const duration = AudioUtils.calculateDuration(1600, 8000);
      expect(duration).toBe(100);
    });

    it('should calculate duration for 16kHz audio', () => {
      // 16000 samples/sec * 2 bytes/sample = 32000 bytes/sec
      // 3200 bytes = 100ms
      const duration = AudioUtils.calculateDuration(3200, 16000);
      expect(duration).toBe(100);
    });
  });

  describe('calculateBytesForDuration', () => {
    it('should calculate bytes for 100ms at 8kHz', () => {
      const bytes = AudioUtils.calculateBytesForDuration(100, 8000);
      expect(bytes).toBe(1600);
    });

    it('should calculate bytes for 1 second at 8kHz', () => {
      const bytes = AudioUtils.calculateBytesForDuration(1000, 8000);
      expect(bytes).toBe(16000);
    });
  });

  describe('generateSilence', () => {
    it('should generate silence buffer of correct size', () => {
      const silence = AudioUtils.generateSilence(100, 8000);
      expect(Buffer.isBuffer(silence)).toBe(true);
      expect(silence.length).toBe(1600);
      
      // All bytes should be 0
      for (let i = 0; i < silence.length; i++) {
        expect(silence[i]).toBe(0);
      }
    });
  });

  describe('generateTone', () => {
    it('should generate tone buffer of correct size', () => {
      const tone = AudioUtils.generateTone(440, 100, 8000);
      expect(Buffer.isBuffer(tone)).toBe(true);
      expect(tone.length).toBe(1600);
    });

    it('should contain non-zero samples for tone', () => {
      const tone = AudioUtils.generateTone(440, 100, 8000);
      let hasNonZero = false;
      
      for (let i = 0; i < tone.length; i += 2) {
        if (tone.readInt16LE(i) !== 0) {
          hasNonZero = true;
          break;
        }
      }
      
      expect(hasNonZero).toBe(true);
    });
  });

  describe('validateSampleRate', () => {
    it('should accept supported sample rates', () => {
      expect(AudioUtils.validateSampleRate(8000)).toBe(true);
      expect(AudioUtils.validateSampleRate(16000)).toBe(true);
      expect(AudioUtils.validateSampleRate(24000)).toBe(true);
    });

    it('should reject unsupported sample rates', () => {
      expect(AudioUtils.validateSampleRate(44100)).toBe(false);
      expect(AudioUtils.validateSampleRate(48000)).toBe(false);
    });
  });
});

