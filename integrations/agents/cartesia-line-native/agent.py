"""Cartesia Line agent ↔ Exotel AgentStream bridge.

Phone PCM (AgentStream) ↔ Cartesia Agents WebSocket
  wss://api.cartesia.ai/agents/stream/{agent_id}

Docs: https://docs.cartesia.ai/line/integrations/websocket-api
"""

from __future__ import annotations

import asyncio
import audioop
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import websockets
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from integrations.agents._shared.wss_server import AgentSession

CARTESIA_API_BASE = os.getenv("CARTESIA_API_BASE", "https://api.cartesia.ai")
CARTESIA_WS_BASE = os.getenv("CARTESIA_WS_BASE", "wss://api.cartesia.ai")
CARTESIA_VERSION_TOKEN = os.getenv("CARTESIA_VERSION_TOKEN", "2026-03-01")
CARTESIA_VERSION_WS = os.getenv("CARTESIA_VERSION_WS", "2025-04-16")
DEFAULT_AGENT_ID = "agent_tSASSRKnELs2aQhcVRnNiq"

# Mute Exotel→Cartesia until greeting starts/finishes so ringback/noise
# does not trigger a false user turn + clear (was ~2.5s of the 4s delay).
DEFAULT_UPLINK_GATE_MS = int(os.getenv("CARTESIA_UPLINK_GATE_MS", "2500"))


class _TokenCache:
    """Reuse access tokens across calls (max 1h; refresh 5 min early)."""

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, api_key: str, *, expires_in: int = 3600) -> str:
        now = time.monotonic()
        if self._token and now < self._expires_at - 300:
            return self._token
        async with self._lock:
            now = time.monotonic()
            if self._token and now < self._expires_at - 300:
                return self._token
            token = await _fetch_agent_access_token(api_key, expires_in=expires_in)
            self._token = token
            self._expires_at = now + expires_in
            return token


_TOKEN_CACHE = _TokenCache()


def _cartesia_input_format(exotel_rate: int) -> tuple[str, int]:
    """Pick Cartesia wire format closest to AgentStream sample rate.

    Cartesia supports mulaw_8000 / pcm_16000 / pcm_24000 / pcm_44100.
    Telephony default: mulaw_8000 (no resample when Exotel is 8 kHz).
    """
    forced = (os.getenv("CARTESIA_INPUT_FORMAT") or "").strip().lower()
    if forced in ("mulaw_8000", "pcm_16000", "pcm_24000", "pcm_44100"):
        rate = int(forced.split("_")[1])
        return forced, rate
    if exotel_rate == 16000:
        return "pcm_16000", 16000
    if exotel_rate == 24000:
        return "pcm_24000", 24000
    return "mulaw_8000", 8000


async def _fetch_agent_access_token(api_key: str, *, expires_in: int = 3600) -> str:
    """Exchange API key for a short-lived token with the agent grant."""
    import urllib.error
    import urllib.request

    url = f"{CARTESIA_API_BASE.rstrip('/')}/access-token"
    body = json.dumps(
        {"grants": {"agent": True}, "expires_in": expires_in}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Cartesia-Version": CARTESIA_VERSION_TOKEN,
            "Content-Type": "application/json",
        },
    )

    def _do() -> dict:
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"access-token HTTP {e.code}: {detail}") from e

    t0 = time.monotonic()
    data = await asyncio.to_thread(_do)
    logger.info(f"cartesia_token_ms={int((time.monotonic() - t0) * 1000)}")
    token = data.get("token")
    if not token:
        raise RuntimeError(f"access-token response missing token: {data}")
    return token


# Public alias for test_ws_connection.py
async def fetch_agent_access_token(api_key: str, *, expires_in: int = 3600) -> str:
    return await _TOKEN_CACHE.get(api_key, expires_in=expires_in)


def _connect_kwargs(headers: dict[str, str]) -> dict[str, Any]:
    """websockets v13+ uses additional_headers; older uses extra_headers."""
    import inspect

    params = inspect.signature(websockets.connect).parameters
    if "additional_headers" in params:
        return {"additional_headers": headers}
    return {"extra_headers": headers}


class CartesiaLineSession(AgentSession):
    def __init__(self, stream_sid: str, sample_rate: int, call_meta: dict):
        super().__init__(stream_sid, sample_rate, call_meta)
        self.api_key = os.getenv("CARTESIA_API_KEY", "").strip()
        self.agent_id = (
            os.getenv("CARTESIA_AGENT_ID", "").strip() or DEFAULT_AGENT_ID
        )
        self.input_format, self.cartesia_rate = _cartesia_input_format(sample_rate)
        self._ws: Any = None
        self._cartesia_stream_id: Optional[str] = None
        self._call_id: Optional[str] = None
        self._ready = asyncio.Event()
        self._closed = False
        self._recv_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._play_task: Optional[asyncio.Task] = None
        self._gate_task: Optional[asyncio.Task] = None
        self._play_q: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        self._up_state = None  # ratecv state Exotel → Cartesia
        self._down_state = None
        # Uplink gate: block media_input until greeting can start cleanly.
        self._uplink_open = False
        self._greeting_seen = False
        self._gate_ms = int(os.getenv("CARTESIA_UPLINK_GATE_MS", str(DEFAULT_UPLINK_GATE_MS)))
        self._t_start = time.monotonic()
        self._t_ack: Optional[float] = None
        self._t_first_media_out: Optional[float] = None
        self._play_buf = bytearray()
        self._play_flush_bytes = max(640, int(self.sample_rate * 0.04) * 2)  # ~40ms

    async def on_start(self) -> None:
        if not self.api_key:
            raise RuntimeError("CARTESIA_API_KEY is required")

        logger.info(
            f"Cartesia Line start agent={self.agent_id} "
            f"exotel_hz={self.sample_rate} format={self.input_format} "
            f"uplink_gate_ms={self._gate_ms}"
        )
        t0 = time.monotonic()
        token = await fetch_agent_access_token(self.api_key)
        t_token = time.monotonic()
        url = f"{CARTESIA_WS_BASE.rstrip('/')}/agents/stream/{self.agent_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Cartesia-Version": CARTESIA_VERSION_WS,
        }
        self._ws = await websockets.connect(
            url,
            open_timeout=30,
            max_size=8 * 1024 * 1024,
            **_connect_kwargs(headers),
        )
        t_ws = time.monotonic()

        start_msg: dict[str, Any] = {
            "event": "start",
            "stream_id": self.stream_sid,
            "config": {
                "input_format": self.input_format,
                "output_audio_delivery": os.getenv(
                    "CARTESIA_OUTPUT_AUDIO_DELIVERY", "as_available"
                ),
            },
            "metadata": {
                "from": (
                    self.call_meta.get("from")
                    or self.call_meta.get("From")
                    or "exotel"
                ),
                "to": (
                    self.call_meta.get("to")
                    or self.call_meta.get("To")
                    or self.call_meta.get("callSid")
                    or self.stream_sid
                ),
            },
        }
        voice_id = (os.getenv("CARTESIA_VOICE_ID") or "").strip()
        if voice_id:
            start_msg["config"]["voice_id"] = voice_id

        await self._ws.send(json.dumps(start_msg))
        self._recv_task = asyncio.create_task(self._recv_loop(), name="cartesia-recv")
        self._play_task = asyncio.create_task(self._playback_loop(), name="cartesia-play")
        self._ping_task = asyncio.create_task(self._ping_loop(), name="cartesia-ping")

        try:
            await asyncio.wait_for(self._ready.wait(), timeout=30.0)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Cartesia agent ack timeout") from exc
        t_ack = time.monotonic()
        self._t_ack = t_ack
        logger.info(
            f"Cartesia ready stream_id={self._cartesia_stream_id} "
            f"call_id={self._call_id} "
            f"token_ms={int((t_token - t0) * 1000)} "
            f"ws_ms={int((t_ws - t_token) * 1000)} "
            f"ack_ms={int((t_ack - t_ws) * 1000)} "
            f"ready_ms={int((t_ack - self._t_start) * 1000)}"
        )
        if self._gate_ms > 0:
            self._gate_task = asyncio.create_task(
                self._uplink_gate_timeout(), name="cartesia-gate"
            )
        else:
            self._uplink_open = True

    async def on_media(self, pcm: bytes) -> None:
        if self._closed or not self._ws or not self._ready.is_set() or not pcm:
            return
        if not self._uplink_open:
            return  # drop early noise so Cartesia can greet without barge-in
        payload = self._exotel_pcm_to_cartesia(pcm)
        if not payload:
            return
        msg = {
            "event": "media_input",
            "stream_id": self._cartesia_stream_id or self.stream_sid,
            "media": {"payload": base64.b64encode(payload).decode("ascii")},
        }
        try:
            await self._ws.send(json.dumps(msg))
        except Exception:
            logger.exception("failed sending media_input to Cartesia")

    async def on_stop(self) -> None:
        self._closed = True
        self._ready.clear()
        await self._flush_play_buf(force=True)
        await self._play_q.put(None)
        for task in (self._ping_task, self._recv_task, self._play_task, self._gate_task):
            if task and not task.done():
                task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close(code=1000, reason="session completed")
            except Exception:
                pass
            self._ws = None
        logger.info(
            f"Cartesia Line stopped stream={self.stream_sid} call_id={self._call_id}"
        )

    async def _uplink_gate_timeout(self) -> None:
        try:
            await asyncio.sleep(self._gate_ms / 1000.0)
        except asyncio.CancelledError:
            return
        if not self._uplink_open:
            self._open_uplink("gate_timeout")

    def _open_uplink(self, reason: str) -> None:
        if self._uplink_open:
            return
        self._uplink_open = True
        age = int((time.monotonic() - self._t_start) * 1000)
        logger.info(f"uplink_open reason={reason} age_ms={age}")

    async def _ping_loop(self) -> None:
        """Reset Cartesia's 180s idle timeout during silence."""
        while not self._closed and self._ws is not None:
            await asyncio.sleep(60)
            if self._closed or self._ws is None:
                break
            try:
                pong = await self._ws.ping()
                await pong
            except Exception:
                logger.warning("Cartesia ping failed")
                break

    async def _playback_loop(self) -> None:
        while True:
            pcm = await self._play_q.get()
            if pcm is None:
                break
            try:
                await self.send_pcm(pcm)
            except Exception:
                logger.exception("Exotel playback failed")

    async def _flush_play_buf(self, *, force: bool = False) -> None:
        if not self._play_buf:
            return
        if not force and len(self._play_buf) < self._play_flush_bytes:
            return
        pcm = bytes(self._play_buf)
        self._play_buf.clear()
        await self._play_q.put(pcm)

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if self._closed:
                    break
                if isinstance(raw, bytes):
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_cartesia_event(data)
        except asyncio.CancelledError:
            raise
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(
                f"Cartesia WS closed code={e.code} reason={e.reason!r}"
            )
        except Exception:
            logger.exception("Cartesia recv loop error")
        finally:
            self._ready.clear()

    async def _handle_cartesia_event(self, data: dict) -> None:
        event = data.get("event")
        if event == "ack":
            self._cartesia_stream_id = data.get("stream_id") or self.stream_sid
            self._call_id = data.get("call_id")
            self._ready.set()
            return

        if event == "media_output":
            payload = (data.get("media") or {}).get("payload")
            if not payload:
                return
            pcm = self._cartesia_payload_to_exotel(base64.b64decode(payload))
            if not pcm:
                return
            if self._t_first_media_out is None:
                self._t_first_media_out = time.monotonic()
                since_start = int((self._t_first_media_out - self._t_start) * 1000)
                since_ack = (
                    int((self._t_first_media_out - self._t_ack) * 1000)
                    if self._t_ack
                    else -1
                )
                logger.info(
                    f"cartesia_first_media_out_ms={since_start} since_ack_ms={since_ack}"
                )
                self._greeting_seen = True
            # Coalesce tiny as_available chunks (~40ms) before pacing to Exotel.
            # Flush immediately on first audio so first_audio_ms stays low.
            self._play_buf.extend(pcm)
            force = self._frames_out == 0 and not self._play_q.qsize()
            await self._flush_play_buf(force=force or len(self._play_buf) >= self._play_flush_bytes)
            return

        if event == "clear":
            # Ignore clears while uplink is gated — those are almost always
            # false barge-ins from early uplink noise, and they wipe the greeting.
            if not self._uplink_open:
                logger.info("ignored Cartesia clear (uplink gated)")
                return
            self._play_buf.clear()
            while not self._play_q.empty():
                try:
                    self._play_q.get_nowait()
                except asyncio.QueueEmpty:
                    break
            await self.clear_playback()
            logger.info("Cartesia clear → Exotel clear")
            return

        if event == "turn_started":
            turn = data.get("turn_started") or {}
            role = turn.get("role")
            logger.info(f"turn_started id={turn.get('id')} role={role}")
            if role == "assistant":
                self._greeting_seen = True
            return

        if event == "turn_output_text_delta":
            delta = data.get("turn_output_text_delta") or {}
            text = delta.get("text") or ""
            if text:
                logger.debug(f"assistant_delta: {text!r}")
            return

        if event == "turn_ended":
            turn = data.get("turn_ended") or {}
            role = turn.get("role")
            logger.info(
                f"turn_ended id={turn.get('id')} role={role} "
                f"text={turn.get('text')!r} interrupted={turn.get('was_interrupted')}"
            )
            # After first assistant turn completes, open mic for the caller.
            if role == "assistant" and self._greeting_seen and not self._uplink_open:
                await self._flush_play_buf(force=True)
                self._open_uplink("assistant_turn_ended")
            return

        if event == "transfer_call":
            transfer = data.get("transfer") or {}
            logger.warning(
                f"transfer_call requested target={transfer.get('target_phone_number')}"
            )
            return

        if event:
            logger.debug(f"ignored Cartesia event={event}")

    def _exotel_pcm_to_cartesia(self, pcm: bytes) -> bytes:
        if len(pcm) % 2:
            pcm = pcm[:-1]
        if not pcm:
            return b""

        if self.input_format.startswith("pcm_"):
            if self.sample_rate == self.cartesia_rate:
                return pcm
            converted, self._up_state = audioop.ratecv(
                pcm, 2, 1, self.sample_rate, self.cartesia_rate, self._up_state
            )
            return converted

        # mulaw_8000
        if self.sample_rate != 8000:
            pcm, self._up_state = audioop.ratecv(
                pcm, 2, 1, self.sample_rate, 8000, self._up_state
            )
        return audioop.lin2ulaw(pcm, 2)

    def _cartesia_payload_to_exotel(self, payload: bytes) -> bytes:
        if not payload:
            return b""

        if self.input_format.startswith("pcm_"):
            pcm = payload
            if len(pcm) % 2:
                pcm = pcm[:-1]
            if self.sample_rate == self.cartesia_rate:
                return pcm
            converted, self._down_state = audioop.ratecv(
                pcm, 2, 1, self.cartesia_rate, self.sample_rate, self._down_state
            )
            return converted

        pcm = audioop.ulaw2lin(payload, 2)
        if self.sample_rate == 8000:
            return pcm
        converted, self._down_state = audioop.ratecv(
            pcm, 2, 1, 8000, self.sample_rate, self._down_state
        )
        return converted


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> CartesiaLineSession:
    return CartesiaLineSession(stream_sid, sample_rate, call_meta)


async def prewarm() -> None:
    """Fetch a token at process start so the first call skips that RTT."""
    api_key = os.getenv("CARTESIA_API_KEY", "").strip()
    if not api_key:
        return
    try:
        await fetch_agent_access_token(api_key)
        logger.info("Cartesia access token prewarmed")
    except Exception:
        logger.exception("Cartesia token prewarm failed")
