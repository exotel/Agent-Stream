"""Shared helpers for Exotel AgentStream PCM media."""

from __future__ import annotations

import audioop
import base64
from typing import Optional
from urllib.parse import parse_qs, urlparse


def sample_rate_from_path(path: str, default: int = 8000) -> int:
    """Parse ?sample-rate= from the WebSocket URL path/query."""
    qs = parse_qs(urlparse(path).query)
    raw = (qs.get("sample-rate") or qs.get("sample_rate") or [None])[0]
    if raw is None:
        return default
    try:
        rate = int(raw)
    except ValueError:
        return default
    return rate if rate in (8000, 16000, 24000) else default


def b64_pcm_decode(payload: str) -> bytes:
    return base64.b64decode(payload)


def b64_pcm_encode(pcm: bytes) -> str:
    return base64.b64encode(pcm).decode("ascii")


def resample_pcm16(pcm: bytes, from_rate: int, to_rate: int) -> bytes:
    if from_rate == to_rate or not pcm:
        return pcm
    converted, _ = audioop.ratecv(pcm, 2, 1, from_rate, to_rate, None)
    return converted


def media_event(stream_sid: str, pcm: bytes, chunk: Optional[int] = None) -> dict:
    body = {
        "event": "media",
        "streamSid": stream_sid,
        "media": {"payload": b64_pcm_encode(pcm)},
    }
    if chunk is not None:
        body["media"]["chunk"] = chunk
    return body


def clear_event(stream_sid: str) -> dict:
    return {"event": "clear", "streamSid": stream_sid}
