"""HTTP adapters for STT / LLM / TTS used by native pipeline recipes."""

from __future__ import annotations

import audioop
import asyncio
import io
import os
import wave

import httpx


def _wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _to_16k(pcm: bytes, sample_rate: int) -> tuple[bytes, int]:
    if sample_rate == 16000:
        return pcm, 16000
    out, _ = audioop.ratecv(pcm, 2, 1, sample_rate, 16000, None)
    return out, 16000


async def stt_deepgram(pcm: bytes, sample_rate: int) -> str:
    key = os.environ["DEEPGRAM_API_KEY"]
    pcm16, rate = _to_16k(pcm, sample_rate)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
            headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
            content=_wav_bytes(pcm16, rate),
        )
        r.raise_for_status()
        data = r.json()
        return (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )


async def stt_assemblyai(pcm: bytes, sample_rate: int) -> str:
    key = os.environ["ASSEMBLYAI_API_KEY"]
    pcm16, rate = _to_16k(pcm, sample_rate)
    async with httpx.AsyncClient(timeout=60.0) as client:
        up = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": key},
            content=_wav_bytes(pcm16, rate),
        )
        up.raise_for_status()
        audio_url = up.json()["upload_url"]
        tr = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": key, "content-type": "application/json"},
            json={"audio_url": audio_url, "speech_model": "universal"},
        )
        tr.raise_for_status()
        tid = tr.json()["id"]
        while True:
            st = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{tid}",
                headers={"authorization": key},
            )
            st.raise_for_status()
            body = st.json()
            if body["status"] == "completed":
                return body.get("text") or ""
            if body["status"] == "error":
                raise RuntimeError(body.get("error"))
            await asyncio.sleep(0.4)


async def stt_sarvam(pcm: bytes, sample_rate: int) -> str:
    key = os.environ["SARVAM_API_KEY"]
    pcm16, rate = _to_16k(pcm, sample_rate)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": key},
            files={"file": ("audio.wav", _wav_bytes(pcm16, rate), "audio/wav")},
            data={
                # saaras:v2 is rejected by current Sarvam API; v3 is the documented default.
                "model": os.getenv("SARVAM_STT_MODEL", "saaras:v3"),
                "mode": "transcribe",
                "language_code": os.getenv("SARVAM_STT_LANGUAGE", "en-IN"),
            },
        )
        r.raise_for_status()
        return r.json().get("transcript") or r.json().get("text") or ""


async def stt_speechmatics(pcm: bytes, sample_rate: int) -> str:
    """Batch-style placeholder — prefer Speechmatics realtime RT for production."""
    _ = (pcm, sample_rate, os.environ.get("SPEECHMATICS_API_KEY"))
    return ""


async def llm_openai(text: str) -> str:
    key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    system = os.getenv("SYSTEM_PROMPT", "You are a concise helpful phone assistant.")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def llm_gemini(text: str) -> str:
    key = os.environ["GOOGLE_API_KEY"]
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    system = os.getenv("SYSTEM_PROMPT", "You are a concise helpful phone assistant.")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": key},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
            },
        )
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)


async def tts_cartesia(text: str, sample_rate: int) -> bytes:
    key = os.environ["CARTESIA_API_KEY"]
    voice = os.environ.get("CARTESIA_VOICE_ID") or "a0e99841-438c-4a64-b679-ae501e7d6091"
    model = os.getenv("CARTESIA_MODEL", "sonic-english")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": key,
                "Cartesia-Version": "2024-06-10",
                "Content-Type": "application/json",
            },
            json={
                "model_id": model,
                "transcript": text,
                "voice": {"mode": "id", "id": voice},
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": sample_rate,
                },
            },
        )
        r.raise_for_status()
        return r.content


async def tts_elevenlabs(text: str, sample_rate: int) -> bytes:
    key = os.environ["ELEVENLABS_API_KEY"]
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    model = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_16000",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": model},
        )
        r.raise_for_status()
        pcm = r.content
        if sample_rate != 16000:
            pcm, _ = audioop.ratecv(pcm, 2, 1, 16000, sample_rate, None)
        return pcm


async def tts_grok(text: str, sample_rate: int) -> bytes:
    key = os.environ["XAI_API_KEY"]
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.x.ai/v1/tts",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"text": text, "model": os.getenv("GROK_TTS_MODEL", "grok-tts")},
        )
        if r.status_code >= 400:
            return b"\x00\x00" * int(sample_rate * 0.1)
        pcm = r.content
        try:
            if sample_rate != 16000:
                pcm, _ = audioop.ratecv(pcm, 2, 1, 16000, sample_rate, None)
        except Exception:
            pass
        return pcm
