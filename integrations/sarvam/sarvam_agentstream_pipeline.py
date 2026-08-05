"""
Sarvam AI + Exotel Agent Stream — minimal production helpers.

Use with the Python bot in this repo or as a reference when implementing
engines/sarvam in stt_engine.py / tts_engine.py.

See SARVAM_AGENTSTREAM_INTEGRATION.md in this folder for the full guide.
"""

from __future__ import annotations

import base64
import io
import os
import struct
import wave
from typing import Optional, Tuple

import requests

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def create_wav(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def resample_linear(pcm: bytes, from_rate: int, to_rate: int) -> bytes:
    """Simple linear resample for 16-bit mono PCM (use scipy/librosa in production at scale)."""
    if from_rate == to_rate:
        return pcm
    import array

    samples = array.array("h")
    samples.frombytes(pcm)
    if len(samples) < 2:
        return pcm
    ratio = to_rate / from_rate
    out_len = int(len(samples) * ratio)
    out = array.array("h")
    for i in range(out_len):
        src = i / ratio
        idx = int(src)
        frac = src - idx
        if idx + 1 < len(samples):
            v = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        else:
            v = samples[min(idx, len(samples) - 1)]
        out.append(int(max(-32768, min(32767, v))))
    return out.tobytes()


def transcribe_sarvam(
    pcm: bytes,
    sample_rate: int,
    api_key: str,
    *,
    timeout: float = 12.0,
) -> Tuple[str, bool]:
    """
    Returns (transcript, rate_limited).
    Upsamples to 16 kHz before STT per production guide.
    """
    pcm_16k = resample_linear(pcm, sample_rate, 16000)
    if len(pcm_16k) < int(0.55 * 16000 * 2):
        return "", False

    wav = create_wav(pcm_16k, 16000)
    resp = requests.post(
        SARVAM_STT_URL,
        headers={"api-subscription-key": api_key},
        files={"file": ("audio.wav", wav, "audio/wav")},
        data={
            "model": "saaras:v3",
            "mode": "transcribe",
            "language_code": "unknown",
        },
        timeout=timeout,
    )
    if resp.status_code == 429:
        return "", True
    resp.raise_for_status()
    return (resp.json().get("transcript") or "").strip(), False


def tts_language_for_text(text: str) -> str:
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return "en-IN" if ascii_count / max(len(text), 1) > 0.85 else "hi-IN"


def synthesize_sarvam(
    text: str,
    api_key: str,
    language: Optional[str] = None,
    *,
    timeout: float = 15.0,
) -> bytes:
    """
    Returns 8 kHz 16-bit mono PCM for Exotel Agent Stream.
    """
    lang = language or tts_language_for_text(text)
    resp = requests.post(
        SARVAM_TTS_URL,
        headers={
            "Content-Type": "application/json",
            "api-subscription-key": api_key,
        },
        json={
            "text": text,
            "target_language_code": lang,
            "speaker": "shubh",
            "model": "bulbul:v3",
            "speech_sample_rate": "24000",
            "output_audio_codec": "linear16",
            "pace": 1.0,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    b64 = resp.json()["audios"][0]
    raw = base64.b64decode(b64)
    if raw[:4] == b"RIFF":
        raw = raw[44:]  # strip minimal WAV header
    pcm_24k = raw
    return resample_linear(pcm_24k, 24000, 8000)


if __name__ == "__main__":
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key:
        print("Set SARVAM_API_KEY to run smoke test")
        raise SystemExit(1)
    pcm8 = synthesize_sarvam("Namaste, yeh ek test hai.", key, "hi-IN")
    print(f"TTS OK: {len(pcm8)} bytes @ 8kHz")
