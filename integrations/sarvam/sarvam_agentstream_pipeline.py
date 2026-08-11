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
    """Resample 16-bit mono PCM. Prefer audioop; fall back to linear interpolation."""
    if from_rate == to_rate or not pcm:
        return pcm
    try:
        import audioop

        out, _ = audioop.ratecv(pcm, 2, 1, from_rate, to_rate, None)
        return out
    except Exception:
        pass

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


def _pcm_from_sarvam_audio(raw: bytes) -> Tuple[bytes, Optional[int]]:
    """Decode Sarvam TTS payload → (pcm16le mono, sample_rate_or_None)."""
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        with wave.open(io.BytesIO(raw), "rb") as wf:
            if wf.getsampwidth() != 2 or wf.getnchannels() not in (1, 2):
                raise ValueError(
                    f"unsupported WAV: channels={wf.getnchannels()} width={wf.getsampwidth()}"
                )
            frames = wf.readframes(wf.getnframes())
            rate = wf.getframerate()
            if wf.getnchannels() == 2:
                # downmix stereo → mono
                import audioop

                frames = audioop.tomono(frames, 2, 0.5, 0.5)
            return frames, rate
    # Raw linear16 mono — caller must know the request rate
    return raw, None


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
    output_sample_rate: int = 8000,
    timeout: float = 15.0,
) -> bytes:
    """
    Returns 16-bit mono PCM for Exotel AgentStream.

    Requests TTS at ``output_sample_rate`` when supported (8000 / 16000 / 24000)
    so we avoid a lossy 24→8 kHz downmix on the telephony path. Falls back to
    24000 + resample if the API rejects the requested rate.
    """
    lang = language or tts_language_for_text(text)
    # Prefer native telephony rate; Sarvam accepts 8000 / 16000 / 22050 / 24000.
    want = output_sample_rate if output_sample_rate in (8000, 16000, 24000) else 8000
    speaker = os.getenv("SARVAM_TTS_SPEAKER", "shubh")
    model = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")

    def _request(rate: int) -> requests.Response:
        return requests.post(
            SARVAM_TTS_URL,
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": api_key,
            },
            json={
                "text": text,
                "target_language_code": lang,
                "speaker": speaker,
                "model": model,
                "speech_sample_rate": str(rate),
                "output_audio_codec": "linear16",
                "pace": 1.0,
            },
            timeout=timeout,
        )

    resp = _request(want)
    request_rate = want
    if resp.status_code >= 400 and want != 24000:
        resp = _request(24000)
        request_rate = 24000
    resp.raise_for_status()
    b64 = resp.json()["audios"][0]
    raw = base64.b64decode(b64)
    pcm, wav_rate = _pcm_from_sarvam_audio(raw)
    src_rate = wav_rate or request_rate
    # If API ignored speech_sample_rate=8000 and returned raw 24 kHz PCM without a
    # WAV header, duration vs spoken length is ~3× short when decoded as 8 kHz.
    if wav_rate is None and request_rate == 8000 and want == 8000 and len(pcm) >= 4:
        words = max(1, len(text.split()))
        expected_ms = max(600, words * 350)  # rough spoken duration
        audio_ms_at_8k = (len(pcm) / 2) / 8000 * 1000
        if audio_ms_at_8k < expected_ms * 0.45:
            src_rate = 24000
    return resample_linear(pcm, src_rate, want)


if __name__ == "__main__":
    key = os.environ.get("SARVAM_API_KEY", "")
    if not key:
        print("Set SARVAM_API_KEY to run smoke test")
        raise SystemExit(1)
    pcm8 = synthesize_sarvam("Namaste, yeh ek test hai.", key, "hi-IN", output_sample_rate=8000)
    ms = (len(pcm8) / 2) / 8000 * 1000
    print(f"TTS OK: {len(pcm8)} bytes @ 8kHz (~{ms:.0f} ms)")
