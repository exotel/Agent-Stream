"""Boot-time Cartesia greeting cache (same voice as live turn TTS)."""

from __future__ import annotations

import array
import time
from typing import Optional

import aiohttp
import websockets
from loguru import logger

from voice_config import (
    CARTESIA_BYTES_URL,
    CARTESIA_VERSION,
    CARTESIA_WS_URL,
    CONTAINER,
    ENCODING,
    SAMPLE_RATE,
    cartesia_api_key,
    cartesia_model,
    cartesia_voice_id,
    greeting_text,
)

# Process cache: (text, voice, model, sample_rate) -> pcm
_GREETING_PCM: Optional[bytes] = None
_GREETING_KEY: Optional[tuple] = None


def trim_leading_silence(
    pcm: bytes,
    *,
    sample_rate: int = SAMPLE_RATE,
    threshold: int = 400,
    max_trim_ms: int = 250,
) -> bytes:
    """Drop near-zero leading PCM16 samples (Cartesia often pads ~100–200ms)."""
    if len(pcm) < 4:
        return pcm
    samples = array.array("h")
    samples.frombytes(pcm)
    max_trim = min(len(samples), int(sample_rate * max_trim_ms / 1000))
    i = 0
    while i < max_trim and abs(samples[i]) < threshold:
        i += 1
    if i == 0:
        return pcm
    trimmed = samples[i:].tobytes()
    logger.info(
        f"greeting silence trim samples={i} (~{1000 * i / sample_rate:.0f}ms) "
        f"bytes {len(pcm)}→{len(trimmed)}"
    )
    return trimmed


async def synthesize_greeting_pcm(session: aiohttp.ClientSession) -> bytes:
    """HTTP /tts/bytes with the same voice/model/rate/encoding as live TTS."""
    api_key = cartesia_api_key()
    if not api_key:
        raise RuntimeError("CARTESIA_API_KEY missing")

    voice = cartesia_voice_id()
    model = cartesia_model()
    text = greeting_text()
    headers = {
        "X-API-Key": api_key,
        "Cartesia-Version": CARTESIA_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "model_id": model,
        "transcript": text,
        "voice": {"mode": "id", "id": voice},
        "language": "en",
        "output_format": {
            "container": CONTAINER,
            "encoding": ENCODING,
            "sample_rate": SAMPLE_RATE,
        },
    }
    t0 = time.perf_counter()
    async with session.post(CARTESIA_BYTES_URL, headers=headers, json=payload) as resp:
        body = await resp.read()
        if resp.status >= 400:
            raise RuntimeError(
                f"Cartesia /tts/bytes HTTP {resp.status}: {body[:300]!r}"
            )
    pcm = trim_leading_silence(body, sample_rate=SAMPLE_RATE)
    ms = (time.perf_counter() - t0) * 1000
    audio_ms = 1000.0 * len(pcm) / (2 * SAMPLE_RATE)
    logger.info(
        f"greeting synthesized voice={voice} model={model} "
        f"text={text!r} tts_ms={ms:.0f} audio_ms={audio_ms:.0f} bytes={len(pcm)}"
    )
    return pcm


async def warm_cartesia_websocket() -> None:
    """Open Cartesia TTS WS once at boot (DNS/TLS warm). Live calls still use bot TTS WS."""
    api_key = cartesia_api_key()
    if not api_key:
        return
    url = f"{CARTESIA_WS_URL}?api_key={api_key}&cartesia_version={CARTESIA_VERSION}"
    try:
        async with websockets.connect(url, open_timeout=10, close_timeout=2) as ws:
            # Handshake only — same endpoint the live CartesiaTTSService uses.
            await ws.ping()
        logger.info("Cartesia TTS websocket warmed")
    except Exception:
        logger.exception("Cartesia websocket warm failed (non-fatal)")


def get_cached_greeting_pcm() -> Optional[bytes]:
    key = (greeting_text(), cartesia_voice_id(), cartesia_model(), SAMPLE_RATE)
    if _GREETING_PCM is None or _GREETING_KEY != key:
        return None
    return _GREETING_PCM


async def warm_greeting_cache() -> None:
    """Synthesize + cache greeting and warm Cartesia WS at process start."""
    global _GREETING_PCM, _GREETING_KEY
    api_key = cartesia_api_key()
    if not api_key:
        logger.warning("CARTESIA_API_KEY missing — greeting cache skipped")
        return

    await warm_cartesia_websocket()

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        pcm = await synthesize_greeting_pcm(session)

    _GREETING_PCM = pcm
    _GREETING_KEY = (
        greeting_text(),
        cartesia_voice_id(),
        cartesia_model(),
        SAMPLE_RATE,
    )
    logger.info(
        f"Greeting cache ready voice={cartesia_voice_id()} "
        f"text={greeting_text()!r} bytes={len(pcm)}"
    )
