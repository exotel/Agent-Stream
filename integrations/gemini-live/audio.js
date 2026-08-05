/**
 * Simple PCM 16-bit mono resampling for Exotel (8/16k) ↔ Gemini (16k in, 24k out).
 * No native deps. For production consider a proper resampler (e.g. sox bindings).
 */
function resample8kTo16k(buffer) {
  const out = Buffer.alloc(buffer.length * 2);
  for (let i = 0; i < buffer.length; i += 2) {
    const sample = buffer.readInt16LE(i);
    out.writeInt16LE(sample, i * 2);
    out.writeInt16LE(sample, i * 2 + 2);
  }
  return out;
}

function resample24kTo16k(buffer) {
  const inSamples = buffer.length / 2;
  const outSamples = Math.floor((inSamples * 16) / 24);
  const out = Buffer.alloc(outSamples * 2);
  for (let i = 0; i < outSamples; i++) {
    const srcIdx = (i * 24) / 16;
    const idx = Math.floor(srcIdx);
    const frac = srcIdx - idx;
    const s0 = idx < inSamples ? buffer.readInt16LE(idx * 2) : 0;
    const s1 = idx + 1 < inSamples ? buffer.readInt16LE((idx + 1) * 2) : s0;
    const sample = Math.round(s0 + frac * (s1 - s0));
    out.writeInt16LE(sample, i * 2);
  }
  return out;
}

function resample24kTo8k(buffer) {
  const inSamples = buffer.length / 2;
  const outSamples = Math.floor((inSamples * 8) / 24);
  const out = Buffer.alloc(outSamples * 2);
  for (let i = 0; i < outSamples; i++) {
    const srcIdx = (i * 24) / 8;
    const idx = Math.min(Math.floor(srcIdx), inSamples - 1);
    const sample = buffer.readInt16LE(idx * 2);
    out.writeInt16LE(sample, i * 2);
  }
  return out;
}

function resampleForGemini(pcmBuffer, fromRate) {
  if (fromRate === 16000) return pcmBuffer;
  if (fromRate === 8000) return resample8kTo16k(pcmBuffer);
  return pcmBuffer;
}

function resampleForExotel(pcmBuffer24k, exotelRate) {
  if (exotelRate === 24000) return pcmBuffer24k;
  if (exotelRate === 16000) return resample24kTo16k(pcmBuffer24k);
  if (exotelRate === 8000) return resample24kTo8k(pcmBuffer24k);
  return resample24kTo8k(pcmBuffer24k);
}

const MIN_CHUNK_BYTES = 3200;
const CHUNK_ALIGNMENT = 320;

function chunkForExotel(buffer) {
  const chunks = [];
  let offset = 0;
  while (offset + MIN_CHUNK_BYTES <= buffer.length) {
    const take = MIN_CHUNK_BYTES;
    chunks.push(buffer.subarray(offset, offset + take));
    offset += take;
  }
  return { chunks, remainder: buffer.subarray(offset) };
}

module.exports = {
  resampleForGemini,
  resampleForExotel,
  chunkForExotel,
  MIN_CHUNK_BYTES,
  CHUNK_ALIGNMENT,
};
