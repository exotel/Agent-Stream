from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import asyncio
import base64
import struct
import os
import audioop  # Import at module level for performance
import ssl

from redis.asyncio import Redis
import websockets
from websockets.protocol import State
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.configs.config import Config
from app.configs.gemini import GEMINI_CONFIG, TOOL_REGISTRY
from app.core.utils.loggers import LoggerFactory
logger = LoggerFactory().get_logger()


class GeminiVoiceAgent:

    def __init__(self, redis: Redis):
        Config.validate()
    
        self.default_sample_rate = Config.DEFAULT_SAMPLE_RATE
        # If set (e.g. from `?sample-rate=16000` on the Exotel WebSocket URL),
        # we will prefer this rate over any negotiated `start.media_format.sample_rate`.
        # NOTE: This assumes Exotel is actually sending audio at this rate.
        self.forced_sample_rate: Optional[int] = None
        self.min_chunk_size_ms = Config.MIN_CHUNK_SIZE_MS
        self.buffer_size_ms = Config.BUFFER_SIZE_MS
        self.audio_buffers: Dict[str, bytes] = {}

        self.exotel_enhanced_events = Config.EXOTEL_MARK_CLEAR_ENHANCED
        self.dynamic_chunk_sizing = Config.DYNAMIC_CHUNK_SIZING
        self.variable_chunk_support = Config.EXOTEL_VARIABLE_CHUNK_SUPPORT
        self.silence_during_gaps = Config.EXOTEL_SILENCE_DURING_GAPS
        self.silence_gap_ms = Config.EXOTEL_SILENCE_GAP_MS

        # Createt State Variable to maintain gemini persistence 
        self.gemini_connections: Dict[str, Any] = {}
        self.response_handler_tasks: Dict[str, asyncio.Task] = {}
        self.exotel_connections: Dict[str, bytes] = {}
        
        self.reconnection_attempts: Dict[str, int] = {}
        self.connection_failures: Dict[str, int] = {}
        self.connection_sample_rates: Dict[str, int] = {}
        self.connection_chunk_sizes: Dict[str, int] = {}
        
        # Audio streaming state for seamless rate conversion
        self.ratecv_states: Dict[str, Any] = {}  # Preserve audioop.ratecv state per connection
        self.audio_locks: Dict[str, asyncio.Lock] = {}  # Prevent buffer race conditions
        # Exotel -> Gemini: preserve resampler state (Gemini Live input expects 16kHz PCM)
        self.exotel_to_gemini_ratecv_states: Dict[str, Any] = {}
        
        # Output jitter buffer for smoother Gemini→Exotel audio
        self.output_buffers: Dict[str, list] = {}
        self.output_buffer_started: Dict[str, bool] = {}
        self.OUTPUT_BUFFER_THRESHOLD = 2  # Buffer 2 packets before starting playback

        # Exotel: raw 8kHz PCM buffer for 320-byte aligned, 3.2KB–100KB chunk compliance
        self.exotel_out_pcm_buffers: Dict[str, bytes] = {}
        self.silence_gap_tasks: Dict[str, asyncio.Task] = {}
        # Serialize bot -> Exotel sends per stream (prevents interleaving bursts).
        self.exotel_send_locks: Dict[str, asyncio.Lock] = {}
        # Track background monitor tasks so we can cancel on cleanup.
        self.monitor_tasks: Dict[str, Dict[str, asyncio.Task]] = {}

        self.event_handler = {
                        "connected": self._handle_exotel_connected,
                        "start": self.handle_exotel_start,
                        "media": self.handle_exotel_media,
                        "mark": self.handle_exotel_mark,
                        "clear": self.handle_exotel_clear,
                        "interrupt": self.handle_exotel_clear,  # Exotel may send event="interrupt" instead of "clear"
                        "stop": self.handle_exotel_stop,
                        "dtmf": self._handle_exotel_dtmf,  # Key presses (bidirectional); log only by default
                    }
        self.redis = redis
        
    async def _set_session_handle(self, stream_sid: str, session_handle: str):
        if not self.redis:
            return
        key = f"sales-agent:gemini:session_handle:{stream_sid}"
        await self.redis.set(key, session_handle, ex=3600)
    
    async def _get_session_handle(self, stream_sid: str):
        if not self.redis:
            return None
        key = f"sales-agent:gemini:session_handle:{stream_sid}"
        handle = await self.redis.get(key)
        if not handle:
            return None
        if isinstance(handle, (bytes, bytearray)):
            return handle.decode("utf-8")
        return str(handle)
    
    async def handle_exotel_websocket(self, websocket, path=None, run_id=None, name=None):
        stream_sid = "unknown"
        customer_name = name  # Store the customer name for personalization
        try:
            try:
                if not run_id:
                    raise ValueError("run_id is required")
            except ValueError as e:
                logger.error(f"Error in handle_exotel_websocket: {e}")
                await websocket.close(code=1003, reason=str(e))
                return
            
            logger.info(f"📞 Starting call session - run_id: {run_id}, customer_name: {customer_name}")
            while True:
                # Check if hangup was initiated or cleanup is in progress
                if stream_sid != "unknown" and stream_sid in self.exotel_connections:
                    if self.exotel_connections[stream_sid].get("hangup_initiated") or \
                       self.exotel_connections[stream_sid].get("cleanup_in_progress"):
                        logger.info(f"🛑 Breaking Exotel loop - hangup/cleanup initiated for {stream_sid}")
                        break
                
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    event = data.get("event","")
                    current_sid = data.get("stream_sid")
                    # Log first few events; always log clear/mark so we can see if Exotel sends interruption
                    if stream_sid == "unknown" or (stream_sid in self.exotel_connections and not self.exotel_connections[stream_sid].get("_first_events_logged")):
                        logger.info(f"📥 Exotel event: event={event!r} stream_sid={current_sid!r} (current stream_sid={stream_sid})")
                        if stream_sid != "unknown" and stream_sid in self.exotel_connections:
                            self.exotel_connections[stream_sid]["_first_events_logged"] = True
                    if event in ("clear", "mark", "interrupt"):
                        logger.info(f"📥 Exotel event (interruption-related): event={event!r} stream_sid={current_sid!r} data_keys={list(data.keys())!r}")

                    if current_sid and stream_sid == "unknown":
                        stream_sid = current_sid
                        logger.info(f"🆔 Stream SID identified: {stream_sid}")

                    if stream_sid != "unknown" and stream_sid not in self.connection_sample_rates:
                        initial_rate = self.forced_sample_rate or self.default_sample_rate
                        self._init_connection_settings(stream_sid, initial_rate, data)

                        now = datetime.now()
                        self.exotel_connections[stream_sid] = {
                                    "websocket": websocket,
                                    "start_time": now,
                                    "call_start_time": now,  # Used by _monitor_call_duration
                                    "gemini_connected": False,
                                    "customer_name": customer_name,
                                    "run_id": run_id,
                                    "hangup_initiated": False,
                                    "cleanup_in_progress": False,
                                    "outbound_sequence": 1,  # Exotel: top-level sequence_number as string
                                    "outbound_media_chunk": 1,  # Exotel media.media.chunk counter (semantic id)
                                    "last_audio_sent_at": now,  # For silence-during-gaps
                                    "metrics": {
                                        "ws_accepted_at": now,
                                        "first_exotel_media_in_at": None,
                                        "first_audio_sent_to_gemini_at": None,
                                        "first_gemini_audio_in_at": None,
                                        "first_bot_audio_out_to_exotel_at": None,
                                    },
                                    "metrics_logged": False,
                        }
                        self.exotel_send_locks[stream_sid] = asyncio.Lock()
                        self.monitor_tasks[stream_sid] = {}
                        logger.info(f"📞 New enhanced connection: {stream_sid} @ {self.connection_sample_rates[stream_sid]}Hz, customer: {customer_name}")
                        if self.silence_during_gaps:
                            self.silence_gap_tasks[stream_sid] = asyncio.create_task(self._silence_during_gaps_loop(stream_sid))

                    if event in self.event_handler:
                        await self.event_handler[event](stream_sid, data)
                    elif event:
                        logger.debug(f"📥 Exotel event not handled: event={event!r} (known: connected, start, media, mark, clear, interrupt, stop, dtmf)")
                    
                    if event == "stop":
                        break

                except WebSocketDisconnect:
                    logger.info(f"🔚 Exotel closed normally: {stream_sid}")
                    break
                except Exception as e:
                    logger.error(f"Error in Exotel loop: {e}")

        finally:
            logger.info(f"🧹 Cleaning up enhanced connection: {stream_sid}")
            await self.cleanup_connections(stream_sid)

    def _init_connection_settings(
        self, stream_sid: str, sample_rate: int, data: Dict
    ):
        self.connection_sample_rates[stream_sid] = sample_rate
        if self.dynamic_chunk_sizing:
            chunk_size_ms = Config.get_adaptive_chunk_size(sample_rate) 
        else:
            chunk_size_ms = self.buffer_size_ms

        chunk_size_bytes = Config.get_chunk_size_bytes(sample_rate, chunk_size_ms)
        self.connection_chunk_sizes[stream_sid] = chunk_size_bytes
        
        # Initialize audio streaming state for seamless conversion
        # self.ratecv_states[stream_sid] = None  # Will be populated by first ratecv call
        # self.audio_locks[stream_sid] = asyncio.Lock()

        logger.info(f"🔧 INITIALIZED CONNECTION {stream_sid}: {sample_rate}Hz, {chunk_size_ms}ms ({chunk_size_bytes}B)")


    async def _handle_exotel_connected(self, stream_sid: str, data: Dict):
        if stream_sid == "unknown":
            logger.warning("⚠️ Ignoring 'connected' event for unknown stream_sid")
            return

        logger.info(f"✅ EXOTEL CONNECTED: {stream_sid}")
        
        try:
            exotel_ws = self.exotel_connections[stream_sid]["websocket"]
            sample_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)
            chunk_size_bytes = self.connection_chunk_sizes.get(stream_sid, Config.AUDIO_CHUNK_SIZE)
            test_tone = self.generate_test_tone(sample_rate=sample_rate)
            test_audio_b64 = base64.b64encode(test_tone).decode()

            # Exotel requires top-level sequence_number as string; stream_sid per doc (snake_case)
            seq = str(self.exotel_connections[stream_sid].get("outbound_sequence", 1))
            self.exotel_connections[stream_sid]["outbound_sequence"] = self.exotel_connections[stream_sid].get("outbound_sequence", 1) + 1
            test_message = {
                "event": "media",
                "sequence_number": seq,
                "stream_sid": stream_sid,
                "media": {
                    "payload": test_audio_b64,
                    "timestamp": self._exotel_timestamp_ms(stream_sid),
                    "chunk": self._get_next_outbound_media_chunk(stream_sid)
                }
            }
            await exotel_ws.send_text(json.dumps(test_message))
            logger.info(f"📤 EXOTEL TEST TONE SENT: sid={stream_sid} seq={seq} bytes={len(test_tone)} ts={test_message['media']['timestamp']}")
            logger.info(f"🔊 SENT TEST TONE TO EXOTEL: {stream_sid}")
        except Exception as e:
            logger.error(f"❌ Error sending enhanced test tone: {e}")

        await self.connect_to_gemini(stream_sid)

    async def handle_exotel_start(self, stream_sid: str, data: Dict):
        # Prefer forced sample rate (from query param) if provided; otherwise use negotiated.
        try:
            forced = self.forced_sample_rate
            if forced:
                self._init_connection_settings(stream_sid, int(forced), data)
            else:
                start = data.get("start", {}) if isinstance(data, dict) else {}
                media_format = start.get("media_format", {}) if isinstance(start, dict) else {}
                negotiated_rate = media_format.get("sample_rate")
                if negotiated_rate:
                    negotiated_rate = int(negotiated_rate)
                    self._init_connection_settings(stream_sid, negotiated_rate, data)
        except Exception:
            pass

        sample_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)
        logger.info(f"🚀 ENHANCED SALES CALL STARTED: {stream_sid} @ {sample_rate}Hz")

        # Ensure Gemini connection exists (handle case where 'connected' event was missed)
        if stream_sid not in self.gemini_connections:
            logger.info(f"⚠️ Gemini connection missing in start event, attempting to connect for {stream_sid}")
            await self.connect_to_gemini(stream_sid)

        # Send an immediate keep-alive media packet so Exotel sees bot→Exotel traffic quickly.
        # This helps avoid early disconnects before the bot generates speech.
        try:
            await self._send_silence_keepalive_to_exotel(stream_sid, reason="start_keep_alive")
        except Exception as e:
            logger.warning(f"Failed to send start keep-alive to Exotel: {e}")

        # Log media format if available
        if "mediaFormat" in data:
            media_format = data["mediaFormat"]
            logger.info(f"📺 Media Format: {json.dumps(media_format, indent=2)}")
    
    async def handle_exotel_media(self, stream_sid: str, data: Dict):
        # handle incoming media from exotel and pass it to gemini for processing
        if stream_sid not in self.gemini_connections:
            # Attempt to connect if missing, with basic retry limit
            failures = self.connection_failures.get(stream_sid, 0)
            if failures < 3:
                logger.warning(f"⚠️ Gemini connection missing in media event, attempting to connect for {stream_sid}")
                await self.connect_to_gemini(stream_sid)
            else:
                # Avoid log spam if we've failed to connect multiple times
                return
            
        payload = data.get("media", {}).get("payload", "")
        if not payload: return 
        try:
            # Exotel media is PCM at Exotel stream sample rate (8k/16k/24k).
            # Gemini Live API input expects 16kHz PCM.
            # Metrics: first Exotel media packet in.
            try:
                if stream_sid in self.exotel_connections:
                    m = self.exotel_connections[stream_sid].get("metrics") or {}
                    if not m.get("first_exotel_media_in_at"):
                        m["first_exotel_media_in_at"] = datetime.now()
                        self.exotel_connections[stream_sid]["metrics"] = m
                        logger.info(f"⏱️ METRIC first_exotel_media_in_at for {stream_sid}")
            except Exception:
                pass
            # Use configured/forced sample rate (default to agent default, not 8k).
            exotel_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)
            
            # Decode PCM audio from Exotel
            pcm_audio = base64.b64decode(payload)
            # Lightweight VAD for barge-in + to flush trailing short utterances to Gemini.
            rms = 0
            try:
                rms = audioop.rms(pcm_audio, 2) if pcm_audio else 0  # width=2 for PCM16
            except Exception:
                rms = 0
            if stream_sid in self.exotel_connections:
                try:
                    conn = self.exotel_connections[stream_sid]
                    now_m = asyncio.get_running_loop().time()
                    # Speech threshold: VAD barge-in when Exotel doesn't send clear. Lower = "stop"/interrupt triggers more easily. Default 750.
                    vad_thr = int(os.getenv("EXOTEL_VAD_RMS_THRESHOLD", "750"))
                    # Silence threshold: end-of-utterance flush. Higher = treat more as silence (noisy lines). Default 250.
                    silence_thr = int(os.getenv("EXOTEL_VAD_SILENCE_RMS", "250"))

                    if rms >= vad_thr:
                        # User is actively speaking.
                        conn["user_speaking_until"] = max(float(conn.get("user_speaking_until", 0.0) or 0.0), now_m + 0.6)

                        # If the user starts talking while bot audio is currently playing, force barge-in.
                        # Works even when Exotel does NOT send a "clear" event (VAD-based interruption).
                        # Short grace period (1.5s default) so interruption works soon after bot starts; increase if greeting gets cut by noise.
                        grace_sec = float(os.getenv("EXOTEL_BOT_GRACE_PERIOD_S", "1.5"))
                        first_bot_out_mono = float(conn.get("first_bot_audio_out_mono", 0.0) or 0.0)
                        grace_over = first_bot_out_mono and (now_m - first_bot_out_mono) >= grace_sec
                        bot_until = float(conn.get("bot_speaking_until", 0.0) or 0.0)
                        if bot_until > now_m and grace_over:
                            drop_duration = 1.0  # Same as clear event: 1s suppression
                            conn["drop_outgoing_until"] = max(float(conn.get("drop_outgoing_until", 0.0) or 0.0), now_m + drop_duration)
                            conn["next_exotel_send_at"] = now_m
                            conn["bot_speaking_until"] = 0
                            if stream_sid in self.exotel_out_pcm_buffers:
                                self.exotel_out_pcm_buffers[stream_sid] = b""
                            await self._send_clear_to_exotel(stream_sid)  # Exotel protocol: tell Exotel to clear unplayed bot audio
                            logger.info(f"🔇 VAD barge-in: stopping bot playback for {stream_sid} (rms={rms} >= {vad_thr}, no Exotel clear)")
                        elif bot_until > now_m and not grace_over and rms >= vad_thr:
                            logger.debug(f"🔇 VAD skip barge-in: grace period for {stream_sid} (rms={rms}, bot_until in {(bot_until - now_m):.2f}s)")

                    if rms <= silence_thr:
                        # Mark last silence time; used to flush short remainder to Gemini.
                        conn["last_silence_at_mono"] = now_m
                except Exception:
                    pass
            enhanced_pcm = self.apply_noise_suppression(pcm_audio, exotel_rate)

            gemini_rate = 16000
            if exotel_rate != gemini_rate:
                state = self.exotel_to_gemini_ratecv_states.get(stream_sid)
                enhanced_pcm, state = audioop.ratecv(
                    enhanced_pcm, 2, 1, exotel_rate, gemini_rate, state
                )
                self.exotel_to_gemini_ratecv_states[stream_sid] = state
            
            # Use lock to prevent buffer race conditions - todo: check usage
            lock = self.audio_locks.get(stream_sid)
            if lock:
                async with lock:
                    if stream_sid not in self.audio_buffers:
                        self.audio_buffers[stream_sid] = b""
                    self.audio_buffers[stream_sid] += enhanced_pcm
            else:
                if stream_sid not in self.audio_buffers:
                    self.audio_buffers[stream_sid] = b""
                self.audio_buffers[stream_sid] += enhanced_pcm

            if stream_sid in self.gemini_connections:
                ws = self.gemini_connections[stream_sid]["websocket"]
                if ws.state == State.OPEN:
                    await self._process_variable_chunks(stream_sid, gemini_rate)
                    # If the user has gone silent, flush any remaining buffer to Gemini.
                    # Without this, short questions (<min chunk) or trailing audio get stuck and Gemini never responds.
                    try:
                        conn = self.exotel_connections.get(stream_sid) or {}
                        last_sil = float(conn.get("last_silence_at_mono", 0.0) or 0.0)
                        now_m = asyncio.get_running_loop().time()
                        flush_window_s = float(os.getenv("EXOTEL_FLUSH_SILENCE_WINDOW_S", "0.7"))
                        flush_timeout_no_silence_s = float(os.getenv("EXOTEL_FLUSH_TIMEOUT_NO_SILENCE_S", "1.2"))
                        user_speaking_until = float(conn.get("user_speaking_until", 0.0) or 0.0)
                        remainder = b""
                        flush_reason = None

                        # (1) Silence-based flush: we saw silence recently (end of utterance).
                        if last_sil and (now_m - last_sil) < flush_window_s:
                            lock = self.audio_locks.get(stream_sid)
                            if lock:
                                async with lock:
                                    remainder = self.audio_buffers.get(stream_sid, b"")
                                    self.audio_buffers[stream_sid] = b""
                            else:
                                remainder = self.audio_buffers.get(stream_sid, b"")
                                self.audio_buffers[stream_sid] = b""
                            flush_reason = "silence"

                        # (2) Fallback: noisy line or quiet speaker → flush after user stopped or when we have buffer but never saw "speech".
                        if not remainder and flush_timeout_no_silence_s > 0:
                            no_silence_long = (not last_sil) or (now_m - last_sil) > flush_timeout_no_silence_s
                            user_stopped = user_speaking_until > 0 and (now_m - user_speaking_until) > 1.0
                            # Also flush when we have buffer but never set user_speaking_until (quiet speaker / low RMS) so Gemini still gets first utterance.
                            buf_len = len(self.audio_buffers.get(stream_sid, b""))
                            min_flush_bytes = Config.get_chunk_size_bytes(gemini_rate, 20)  # at least ~20ms at 16kHz
                            has_buffer = buf_len >= min_flush_bytes
                            if no_silence_long and (user_stopped or (has_buffer and user_speaking_until == 0)):
                                lock = self.audio_locks.get(stream_sid)
                                if lock:
                                    async with lock:
                                        remainder = self.audio_buffers.get(stream_sid, b"")
                                        self.audio_buffers[stream_sid] = b""
                                else:
                                    remainder = self.audio_buffers.get(stream_sid, b"")
                                    self.audio_buffers[stream_sid] = b""
                                flush_reason = "timeout_no_silence" if user_stopped else "timeout_quiet_speaker"

                        if remainder:
                            await self._send_audio_to_gemini(stream_sid, remainder, gemini_rate)
                            if flush_reason:
                                logger.info(f"📤 Flush to Gemini: {stream_sid} reason={flush_reason} bytes={len(remainder)}")
                    except Exception:
                        pass
                
        except Exception as e:
            logger.error(f"❌ Error processing enhanced buffered audio: {e}")

    async def _process_variable_chunks(self, stream_sid: str, sample_rate: int):
        """Process audio with variable chunk sizes (Enhanced Exotel feature)"""
        # Gemini benefits from smaller chunks for responsiveness; Exotel's 3.2KB minimum applies
        # to bot->Exotel, not user->Gemini.
        gemini_min_ms = int(os.getenv("GEMINI_MIN_CHUNK_MS", "20"))
        min_chunk_bytes = Config.get_chunk_size_bytes(sample_rate, gemini_min_ms)
        max_chunk_bytes = Config.get_chunk_size_bytes(sample_rate, Config.MAX_CHUNK_SIZE_MS)
        
        # Use lock to prevent buffer race conditions
        lock = self.audio_locks.get(stream_sid)
        if lock:
            async with lock:
                buffer = self.audio_buffers.get(stream_sid, b"")
                chunks_to_send = []
                
                # IMPORTANT: Send small, steady chunks to Gemini to minimize latency.
                # The previous logic could drain the entire buffer at once, increasing
                # end-to-end delay (Gemini turn detection + response start).
                while len(buffer) >= min_chunk_bytes:
                    take = min_chunk_bytes
                    # Safety cap: never exceed max_chunk_bytes even if misconfigured.
                    if take > max_chunk_bytes:
                        take = max_chunk_bytes
                    chunk = buffer[:take]
                    buffer = buffer[take:]
                    chunks_to_send.append(chunk)
                
                self.audio_buffers[stream_sid] = buffer
        else:
            buffer = self.audio_buffers.get(stream_sid, b"")
            chunks_to_send = []
            while len(buffer) >= min_chunk_bytes:
                take = min_chunk_bytes
                if take > max_chunk_bytes:
                    take = max_chunk_bytes
                chunk = buffer[:take]
                buffer = buffer[take:]
                chunks_to_send.append(chunk)
            self.audio_buffers[stream_sid] = buffer
        
        # Send chunks outside the lock to avoid blocking
        for chunk in chunks_to_send:
            await self._send_audio_to_gemini(stream_sid, chunk, sample_rate)


    async def connect_to_gemini(self, stream_sid: str):
        """Connect to Gemini Live API for audio processing"""
        try:
            sample_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)
            ws_url = f"{Config.GEMINI_LIVE_WS_URL}?key={Config.GEMINI_LIVE_WS_API_KEY}"

            # Fix macOS/python TLS trust issues by using certifi CA bundle if available.
            # Without this, websockets.connect may fail with CERTIFICATE_VERIFY_FAILED.
            ssl_ctx = None
            try:
                import certifi  # type: ignore
                ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                # Fall back to system default CA set
                ssl_ctx = ssl.create_default_context()

            # Connect to Gemini Live API with optimized settings for real-time audio
            gemini_ws = await websockets.connect(
                ws_url,
                ssl=ssl_ctx,
                # IMPORTANT: disable client ping/pong keepalive here.
                # We observed `keepalive ping timeout` (1011) closing the Gemini socket, which then
                # caused Exotel streams to end and Exotel to report `DisconnectedBy: bot`.
                # We'll rely on read/write errors and our own reconnection logic instead.
                ping_interval=None,
                ping_timeout=None,
                close_timeout=2,        # Don't wait long on close
                max_size=1_048_576,     # 1MB max message size
                compression=None        # Disable compression for real-time audio
            )

            self.gemini_connections[stream_sid] = {
                "websocket": gemini_ws,
                "sample_rate": sample_rate,
                "input_format": "pcm16",
                "output_format": "pcm24"
            }
            self.connection_failures[stream_sid] = 0

            if stream_sid in self.exotel_connections:
                self.exotel_connections[stream_sid]["gemini_connected"] = True

            await self._init_gemini_session(stream_sid)
            if stream_sid in self.response_handler_tasks:
                self.response_handler_tasks[stream_sid].cancel()
            
            self.response_handler_tasks[stream_sid] = asyncio.create_task(self.handle_gemini_responses(stream_sid, gemini_ws))
            
            if self.reconnection_attempts.get(stream_sid, 0) == 0:
                self.monitor_tasks.setdefault(stream_sid, {})
                # Avoid duplicating tasks if reconnect logic calls connect_to_gemini again.
                if "duration" not in self.monitor_tasks[stream_sid] or self.monitor_tasks[stream_sid]["duration"].done():
                    self.monitor_tasks[stream_sid]["duration"] = asyncio.create_task(self._monitor_call_duration(stream_sid))
                if "health" not in self.monitor_tasks[stream_sid] or self.monitor_tasks[stream_sid]["health"].done():
                    self.monitor_tasks[stream_sid]["health"] = asyncio.create_task(self._monitor_connection_health(stream_sid))

        except Exception as e:
            logger.error(f"❌ Failed to connect to Gemini for {stream_sid}: {e}", exc_info=True)
            self.connection_failures[stream_sid] = self.connection_failures.get(stream_sid, 0) + 1
    
    async def _process_fixed_chunks(self, stream_sid: str, target_chunk_bytes: int, sample_rate: int):
        """Process audio with traditional fixed chunk sizes"""
        buffer = self.audio_buffers[stream_sid]
        # Check if we have enough data for target chunk size
        if len(buffer) >= target_chunk_bytes:
            # Extract target chunk
            chunk = buffer[:target_chunk_bytes]
            self.audio_buffers[stream_sid] = buffer[target_chunk_bytes:]
            
            # Send to GEMINI
            await self._send_audio_to_gemini(stream_sid, chunk, sample_rate)
            
            chunk_ms = (len(chunk) * 1000) // (sample_rate * 2)  # 16-bit PCM
            logger.info(f"📤 FIXED CHUNK SENT: {len(chunk)} bytes ({chunk_ms}ms) @ {sample_rate}Hz [aligned to 320B]")

    async def _send_audio_to_gemini(self, stream_sid: str, chunk: bytes, sample_rate: int):
        """Send audio chunk to GEMINI with connection validation"""
        try:
            # Validate connection exists
            if stream_sid not in self.gemini_connections:
                logger.warning(f"⚠️ No Gemini connection for {stream_sid}, skipping audio chunk")
                return
            
            gemini_config = self.gemini_connections[stream_sid]
            gemini_ws = gemini_config.get("websocket")
            
            # Validate WebSocket is open
            if not gemini_ws or gemini_ws.state != State.OPEN:
                logger.warning(f"⚠️ Gemini WebSocket not open for {stream_sid}, skipping audio chunk")
                return
            
            # Gemini Live input is always 16kHz PCM in our pipeline.
            # Some call paths (e.g. _commit_audio_buffer) used to accidentally pass Exotel's 8kHz rate,
            # which mislabels 16kHz PCM as 8kHz and can break turn detection/recognition after a few turns.
            if int(sample_rate) != 16000:
                logger.warning(f"⚠️ Forcing Gemini input rate to 16000Hz (got {sample_rate}) for {stream_sid}")
                sample_rate = 16000
            GEMINI_MIME_TYPE = f"audio/pcm;rate={sample_rate}"
            gemini_audio = base64.b64encode(chunk).decode("utf-8")
            
            # Metrics: first audio sent to Gemini for this stream.
            try:
                if stream_sid in self.exotel_connections:
                    m = self.exotel_connections[stream_sid].get("metrics") or {}
                    if not m.get("first_audio_sent_to_gemini_at"):
                        m["first_audio_sent_to_gemini_at"] = datetime.now()
                        self.exotel_connections[stream_sid]["metrics"] = m
                        logger.info(f"⏱️ METRIC first_audio_sent_to_gemini_at for {stream_sid}")
            except Exception:
                pass
        
            msg = {
                "realtimeInput": {
                    "audio": {
                        "mimeType": GEMINI_MIME_TYPE,
                        "data": gemini_audio
                    }
                }
            }

            await gemini_ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"❌ Error sending audio to Gemini: {e}")
            # Mark connection as potentially failed for reconnection handling
            if stream_sid in self.connection_failures:
                self.connection_failures[stream_sid] += 1
    

    async def _init_gemini_session(self, stream_sid: str):
        """Initialize Gemini session with configuration"""
        try:
            gemini_ws = self.gemini_connections[stream_sid]["websocket"]
            sample_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)

            session_handle = await self._get_session_handle(stream_sid)

            # Get customer name for personalization
            customer_name = None
            if stream_sid in self.exotel_connections:
                customer_name = self.exotel_connections[stream_sid].get("customer_name")

            # Prepare Gemini session config with personalized system instruction
            import copy
            session_config = copy.deepcopy(GEMINI_CONFIG)
            personalized_instruction = Config.get_personalized_system_instruction(customer_name)
            session_config["setup"]["systemInstruction"]["parts"] = [
                {"text": personalized_instruction}
            ]

            # Enable session resumption with existing handle if available
            if session_handle:
                # Only add sessionResumption config when we have a handle to resume
                session_config["setup"]["sessionResumption"] = {
                    "handle": session_handle
                }
                logger.info(f"🔄 RESUMING SESSION with handle for {stream_sid}")
            else:
                # For new sessions, add empty sessionResumption to enable the feature
                session_config["setup"]["sessionResumption"] = {}
                logger.info(f"🆕 STARTING NEW SESSION for {stream_sid}")

            # Send session configuration
            await gemini_ws.send(json.dumps(session_config))
            logger.info(f"🔧 GEMINI SESSION CONFIGURED for {stream_sid} @ {sample_rate}Hz (customer: {customer_name})")

            # Defer greeting until after setupComplete (see handle_gemini_responses).
            # Sending clientContent before Gemini is ready can result in the bot never speaking.
            if not session_handle:
                self.gemini_connections[stream_sid]["send_greeting_after_setup"] = True

        except Exception as e:
            logger.error(f"❌ Error initializing Gemini session for {stream_sid}: {e}", exc_info=True)

    async def _execute_tool(self, function_name: str, args: dict, stream_sid: str = None) -> dict:
        """Execute tool function and return result"""
        try:
            tool_fn = TOOL_REGISTRY.get(function_name)
            if tool_fn is None:
                return {"error": f"Unknown function: {function_name}"}
            
            result = tool_fn(**args)
            
            # Special handling for end_conversation tool
            if function_name == "end_conversation" and stream_sid:
                logger.info(f"🔔 END_CONVERSATION TOOL CALLED for {stream_sid}")
                # Schedule hangup after a brief delay to allow response
                asyncio.create_task(self._delayed_hangup(stream_sid, "user_conversation_ending", delay=2))
            
            return result
        except Exception as e:
            logger.error(f"❌ Error executing tool {function_name}: {e}")
            return {"error": str(e)}

    async def handle_gemini_responses(self, stream_sid: str, gemini_ws):
        """Handle responses from Gemini Live API"""
        try:
            async for message in gemini_ws:
                try:
                    data = json.loads(message)
                    if "setupComplete" in data:
                        logger.info(f"✅ Gemini setup complete for {stream_sid}")
                        # Send initial greeting only after setup is ready (so bot speaks).
                        try:
                            if self.gemini_connections.get(stream_sid, {}).pop("send_greeting_after_setup", False):
                                await self.send_initial_greeting(stream_sid)
                        except Exception as e:
                            logger.error(f"❌ Error sending greeting after setup: {e}")
                        continue
                    
                    if "sessionResumptionUpdate" in data:
                        update = data["sessionResumptionUpdate"]
                        if update.get("resumable") and update.get("newHandle"):
                            await self._set_session_handle(stream_sid, update["newHandle"])
                            logger.info(f"💾 Session handle checkpointed for stream id {stream_sid}: {update['newHandle'][:20]}....")
                        
                        continue
                        
                    if "toolCall" in data and data["toolCall"] is not None:
                        tool_call = data["toolCall"]
                        # Note: Gemini sends "functionCalls" (plural) as an array
                        function_calls = tool_call.get("functionCalls", [])
                        
                        if not function_calls:
                            logger.warning(f"⚠️ Received toolCall with no functionCalls: {tool_call}")
                            continue
                        
                        function_responses = []
                        for fc in function_calls:
                            function_name = fc.get("name")
                            function_args = fc.get("args", {})
                            call_id = fc.get("id")
                            
                            logger.info(f"🔧 Tool Call: {function_name} (id={call_id}) with args: {function_args}")
                            
                            # Execute the function (pass stream_sid for special handling)
                            result = await self._execute_tool(function_name, function_args, stream_sid=stream_sid)
                            
                            # Response must include the id to match the function call
                            function_responses.append({
                                "id": call_id,
                                "name": function_name,
                                "response": result
                            })
                        
                        # Send tool response back to Gemini
                        tool_response_msg = {
                            "toolResponse": {
                                "functionResponses": function_responses
                            }
                        }
                        await gemini_ws.send(json.dumps(tool_response_msg))
                        logger.info(f"📤 Sent tool response for {[fc.get('name') for fc in function_calls]}")
                        continue

                    server_content = data.get("serverContent", {})
                    if not server_content:
                        continue
                    
                    # Check for user transcript in turn for conversation ending detection
                    if "turnComplete" in server_content and server_content.get("turnComplete"):
                        # Try to extract user text from grounding metadata or model turn
                        user_text = ""
                        if "groundingMetadata" in server_content:
                            user_text = server_content.get("groundingMetadata", {}).get("userInput", "")

                        if user_text:
                            # Detect if user is trying to end conversation
                            is_ending = await self._detect_conversation_ending(user_text)
                            if is_ending:
                                logger.info(f"👋 USER CONVERSATION ENDING DETECTED for {stream_sid}")
                                asyncio.create_task(self._initiate_hangup(stream_sid, "user_conversation_ending"))

                    # Handle interruption (Gemini barge-in signal). Per Exotel protocol we send "clear" to Exotel so they clear unplayed bot audio.
                    if server_content.get("interrupted"):
                        logger.info(f"⚠️ Gemini interrupted turn for {stream_sid}; stopping bot playback locally")
                        try:
                            if stream_sid in self.exotel_out_pcm_buffers:
                                self.exotel_out_pcm_buffers[stream_sid] = b""
                            if stream_sid in self.exotel_connections:
                                conn = self.exotel_connections[stream_sid]
                                now_m = asyncio.get_running_loop().time()
                                conn["next_exotel_send_at"] = now_m
                                conn["drop_outgoing_until"] = now_m + 0.8
                            await self._send_clear_to_exotel(stream_sid)
                        except Exception as e:
                            logger.warning(f"Failed to apply local interrupt for {stream_sid}: {e}")
                        continue

                    # Handle model turn (audio response)
                    if "modelTurn" in server_content and "parts" in server_content.get("modelTurn", {}):
                        parts = server_content.get("modelTurn", {}).get("parts", [])
                        for part in parts:
                            # Skip thought parts # fallback
                            if "thought" in part and part["thought"]:
                                continue

                            # Process audio data
                            if "inlineData" in part:
                                audio_payload = part.get("inlineData", {}).get("data", "")
                                if audio_payload and stream_sid in self.exotel_connections:
                                    # Metrics: first Gemini audio payload received.
                                    try:
                                        m = self.exotel_connections[stream_sid].get("metrics") or {}
                                        if not m.get("first_gemini_audio_in_at"):
                                            m["first_gemini_audio_in_at"] = datetime.now()
                                            self.exotel_connections[stream_sid]["metrics"] = m
                                            logger.info(f"⏱️ METRIC first_gemini_audio_in_at for {stream_sid}")
                                    except Exception:
                                        pass
                                    await self._send_audio_to_exotel(stream_sid, audio_payload)


                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error from Gemini: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing Gemini response: {e}")

        except websockets.ConnectionClosed as e:
            logger.warning(f"⚠️ Gemini WebSocket connection closed: {e}")
            # Attempt to reconnect using session resumption
            await self._handle_gemini_disconnection(stream_sid)
        except Exception as e:
            logger.error(f"❌ Error in Gemini response handler: {e}")
            # Attempt to reconnect on unexpected errors
            await self._handle_gemini_disconnection(stream_sid)

    def _get_next_outbound_sequence(self, stream_sid: str) -> str:
        """Return current outbound sequence as string and increment. Exotel expects sequence_number as string."""
        conn = self.exotel_connections.get(stream_sid)
        if not conn:
            return "1"
        seq = conn.get("outbound_sequence", 1)
        conn["outbound_sequence"] = seq + 1
        return str(seq)

    def _exotel_timestamp_ms(self, stream_sid: str) -> str:
        """
        Exotel expects media.timestamp as milliseconds from the start of the stream,
        not epoch time.
        """
        conn = self.exotel_connections.get(stream_sid) or {}
        start = conn.get("call_start_time") or conn.get("start_time")
        if not start:
            return "0"
        try:
            ms = int((datetime.now() - start).total_seconds() * 1000)
            return str(max(ms, 0))
        except Exception:
            return "0"

    def _get_next_outbound_media_chunk(self, stream_sid: str) -> str:
        """Incrementing counter for Exotel media.media.chunk as string (Exotel expects string)."""
        conn = self.exotel_connections.get(stream_sid)
        if not conn:
            return "1"
        c = int(conn.get("outbound_media_chunk", 1))
        conn["outbound_media_chunk"] = c + 1
        return str(c)

    async def _send_clear_to_exotel(self, stream_sid: str):
        """Tell Exotel to clear audio we sent but not yet played (per Exotel protocol). Use when we interrupt (VAD barge-in or Gemini interrupted)."""
        if stream_sid not in self.exotel_connections:
            return
        exotel_ws = self.exotel_connections[stream_sid]["websocket"]
        if not hasattr(exotel_ws, 'client_state') or exotel_ws.client_state.name == 'DISCONNECTED':
            return
        try:
            clear_msg = {"event": "clear", "stream_sid": stream_sid}
            await exotel_ws.send_text(json.dumps(clear_msg))
            logger.info(f"📤 EXOTEL CLEAR SENT: {stream_sid} (clear unplayed bot audio)")
        except Exception as e:
            logger.warning(f"Failed to send clear to Exotel: {e}")

    async def _send_mark_to_exotel(self, stream_sid: str, name: str = "playback_chunk"):
        """Send mark event to Exotel after media (or keepalive). Exotel doc: event, sequence_number (string), stream_sid, mark.name (timestamp optional)."""
        if stream_sid not in self.exotel_connections:
            return
        exotel_ws = self.exotel_connections[stream_sid]["websocket"]
        if not hasattr(exotel_ws, 'client_state') or exotel_ws.client_state.name == 'DISCONNECTED':
            return
        # Caller must hold exotel_send_locks[stream_sid] where needed (keepalive/send loop); we don't take it here to avoid deadlock.
        seq = self._get_next_outbound_sequence(stream_sid)
        ts_ms = self._exotel_timestamp_ms(stream_sid)
        mark_msg = {
            "event": "mark",
            "sequence_number": seq,
            "stream_sid": stream_sid,
            "mark": {"name": name, "timestamp": ts_ms}
        }
        await exotel_ws.send_text(json.dumps(mark_msg))

    async def _send_silence_keepalive_to_exotel(self, stream_sid: str, reason: str = "keep_alive"):
        """Send one minimal valid media packet + mark to keep the Exotel stream alive."""
        if stream_sid not in self.exotel_connections:
            return
        conn = self.exotel_connections[stream_sid]
        if conn.get("hangup_initiated"):
            return
        exotel_ws = conn.get("websocket")
        if not exotel_ws or not hasattr(exotel_ws, "client_state") or exotel_ws.client_state.name == "DISCONNECTED":
            return

        silence_chunk = bytes(Config.MIN_CHUNK_BYTES)  # 3200B of zeros, PCM16 mono
        lock = self.exotel_send_locks.get(stream_sid)
        if lock is None:
            lock = asyncio.Lock()
            self.exotel_send_locks[stream_sid] = lock
        async with lock:
            seq = self._get_next_outbound_sequence(stream_sid)
            chunk_id = self._get_next_outbound_media_chunk(stream_sid)
            media_message = {
                "event": "media",
                "sequence_number": seq,
                "stream_sid": stream_sid,
                "media": {
                    "payload": base64.b64encode(silence_chunk).decode("utf-8"),
                    "timestamp": self._exotel_timestamp_ms(stream_sid),
                    "chunk": chunk_id,
                },
            }
            await exotel_ws.send_text(json.dumps(media_message))
            logger.info(f"📤 EXOTEL KEEPALIVE SENT: sid={stream_sid} seq={seq} chunk={chunk_id} bytes={len(silence_chunk)} ts={media_message['media']['timestamp']}")
            await self._send_mark_to_exotel(stream_sid, reason)
            conn["last_audio_sent_at"] = datetime.now()

    async def _silence_during_gaps_loop(self, stream_sid: str):
        """Send silent PCM during gaps to improve RX count and prevent timeouts (Exotel recommendation)."""
        try:
            gap_sec = self.silence_gap_ms / 1000.0
            silence_chunk = bytes(Config.MIN_CHUNK_BYTES)  # 3200 bytes of zeros, 8kHz 16-bit mono
            while stream_sid in self.exotel_connections:
                await asyncio.sleep(gap_sec)
                if stream_sid not in self.exotel_connections or self.exotel_connections[stream_sid].get("hangup_initiated"):
                    break
                conn = self.exotel_connections[stream_sid]
                last = conn.get("last_audio_sent_at")
                if last is None:
                    continue
                if (datetime.now() - last).total_seconds() < gap_sec:
                    continue
                exotel_ws = conn.get("websocket")
                if not exotel_ws or not hasattr(exotel_ws, 'client_state') or exotel_ws.client_state.name == 'DISCONNECTED':
                    break
                lock = self.exotel_send_locks.get(stream_sid)
                if lock is None:
                    lock = asyncio.Lock()
                    self.exotel_send_locks[stream_sid] = lock
                async with lock:
                    seq = self._get_next_outbound_sequence(stream_sid)
                    chunk_id = self._get_next_outbound_media_chunk(stream_sid)
                    payload_b64 = base64.b64encode(silence_chunk).decode("utf-8")
                    media_message = {
                        "event": "media",
                        "sequence_number": seq,
                        "stream_sid": stream_sid,
                        "media": {"payload": payload_b64, "timestamp": self._exotel_timestamp_ms(stream_sid), "chunk": chunk_id}
                    }
                    await exotel_ws.send_text(json.dumps(media_message))
                    logger.info(f"📤 EXOTEL SILENCE GAP SENT: sid={stream_sid} seq={seq} chunk={chunk_id} bytes={len(silence_chunk)} ts={media_message['media']['timestamp']}")
                    await self._send_mark_to_exotel(stream_sid, "keep_alive")
                    conn["last_audio_sent_at"] = datetime.now()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Error in silence-during-gaps loop: {e}")

    async def _handle_gemini_disconnection(self, stream_sid: str):
        """Handle Gemini disconnection and attempt reconnection with session resumption"""
        try:
            # Check if hangup was already initiated or cleanup is in progress - do not reconnect
            connection_info = self.exotel_connections.get(stream_sid, {})
            if connection_info.get("hangup_initiated") or connection_info.get("cleanup_in_progress"):
                logger.info(f"🛑 Hangup/cleanup already initiated for {stream_sid}, skipping reconnection")
                return

            attempts = self.reconnection_attempts.get(stream_sid, 0) + 1 
            self.reconnection_attempts[stream_sid] = attempts

            if attempts > 2:
                logger.error(f"❌ Max reconnections reached for {stream_sid}")
                await self._initiate_hangup(stream_sid, "max_reconnection_attempts")
                return
            
            logger.info(f"🔄 ATTEMPTING RECONNECTION #{self.reconnection_attempts[stream_sid]} for {stream_sid}")
            
            # Cancel old response handler task if exists
            if stream_sid in self.response_handler_tasks:
                old_task = self.response_handler_tasks[stream_sid]
                if not old_task.done():
                    old_task.cancel()
                del self.response_handler_tasks[stream_sid]
            
            # Wait a bit before reconnecting
            await asyncio.sleep(0.5)
            
            # Reconnect using the stored session handle
            await self.connect_to_gemini(stream_sid)
                
        except Exception as e:
            logger.error(f"❌ Error handling Gemini disconnection: {e}")
            
    async def _send_audio_to_exotel(self, stream_sid: str, audio_payload: str):
        """Send audio from Gemini to Exotel: 320-byte aligned, 3.2KB–100KB chunks, sequence_number as string, mark after media."""
        try:
            if stream_sid not in self.exotel_connections or self.exotel_connections[stream_sid].get("hangup_initiated"):
                return
            conn = self.exotel_connections[stream_sid]
            exotel_ws = conn["websocket"]
            if not hasattr(exotel_ws, 'client_state') or exotel_ws.client_state.name == 'DISCONNECTED':
                return

            # If caller barged-in (Exotel "clear"), drop any pending bot audio briefly.
            # This makes interruption feel immediate and prevents "talking over" the user.
            try:
                drop_until = float(conn.get("drop_outgoing_until", 0.0) or 0.0)
            except Exception:
                drop_until = 0.0
            now_mono = asyncio.get_running_loop().time()
            # IMPORTANT: only treat "hard drop" (clear/barge-in) as mandatory suppression.
            # Do NOT pause model audio just because inbound RMS is high; that can permanently mute the bot
            # on noisy lines. Instead we convert RMS -> drop_outgoing_until ONLY when the bot is speaking
            # (see `handle_exotel_media`).
            if drop_until and now_mono < drop_until:
                self.exotel_out_pcm_buffers[stream_sid] = b""
                # Debug: log rare drops at most once every 2s per stream.
                try:
                    last_log = float(conn.get("last_drop_log_at", 0.0) or 0.0)
                    if (now_mono - last_log) > 2.0:
                        conn["last_drop_log_at"] = now_mono
                        logger.info(f"🔇 DROPPING bot audio for {stream_sid} (drop_outgoing_until in {(drop_until-now_mono):.2f}s)")
                except Exception:
                    pass
                return

            pcm_data_24k = base64.b64decode(audio_payload)
            # Gemini Live native-audio outputs 24kHz PCM. Convert to Exotel stream rate (8k/16k/24k).
            target_rate = self.connection_sample_rates.get(stream_sid, 8000)
            current_state = self.ratecv_states.get(stream_sid)
            converted_pcm, new_state = audioop.ratecv(
                pcm_data_24k, 2, 1, 24000, target_rate, current_state
            )
            self.ratecv_states[stream_sid] = new_state

            # Exotel: accumulate PCM and send only 320-byte aligned chunks in [3.2KB, 100KB]
            if stream_sid not in self.exotel_out_pcm_buffers:
                self.exotel_out_pcm_buffers[stream_sid] = b""
            self.exotel_out_pcm_buffers[stream_sid] += converted_pcm

            buf = self.exotel_out_pcm_buffers[stream_sid]
            min_bytes = Config.MIN_CHUNK_BYTES
            max_bytes = Config.MAX_CHUNK_BYTES
            align = Config.CHUNK_ALIGNMENT

            while len(buf) >= min_bytes:
                # If user interrupted (clear event), stop sending immediately for natural conversation.
                now_mono = asyncio.get_running_loop().time()
                drop_until = float(conn.get("drop_outgoing_until", 0.0) or 0.0)
                if drop_until and now_mono < drop_until:
                    self.exotel_out_pcm_buffers[stream_sid] = b""
                    break
                # Re-read buffer in case clear cleared it between iterations
                buf = self.exotel_out_pcm_buffers[stream_sid]
                if len(buf) < min_bytes:
                    break

                # Always send fixed-size frames (min_bytes), to avoid bursty/variable packet sizes.
                # Bursty sends cause audible jitter on Exotel playback.
                take = min_bytes
                if take > len(buf):
                    break
                chunk = buf[:take]
                self.exotel_out_pcm_buffers[stream_sid] = buf[take:]
                buf = self.exotel_out_pcm_buffers[stream_sid]

                # Pace outbound audio in (near) real-time based on audio duration.
                # This avoids sending multiple frames back-to-back (which creates jitter).
                bytes_per_second = int(target_rate) * 2  # PCM16 mono
                chunk_duration_s = max(len(chunk) / float(bytes_per_second), 0.0)
                next_send_at = conn.get("next_exotel_send_at")
                if not isinstance(next_send_at, (int, float)):
                    next_send_at = now_mono
                # If next_send_at is far in the past (e.g. after silence gap), use now to avoid burst catch-up and jitter.
                if now_mono - float(next_send_at) > 0.5:
                    next_send_at = now_mono
                wait_s = float(next_send_at) - now_mono
                if wait_s > 0:
                    await asyncio.sleep(wait_s)
                    now_mono = asyncio.get_running_loop().time()
                conn["next_exotel_send_at"] = max(float(next_send_at), now_mono) + chunk_duration_s

                lock = self.exotel_send_locks.get(stream_sid)
                if lock is None:
                    lock = asyncio.Lock()
                    self.exotel_send_locks[stream_sid] = lock
                async with lock:
                    seq = self._get_next_outbound_sequence(stream_sid)
                    chunk_id = self._get_next_outbound_media_chunk(stream_sid)
                    payload_b64 = base64.b64encode(chunk).decode("utf-8")
                    media_message = {
                        "event": "media",
                        "sequence_number": seq,
                        "stream_sid": stream_sid,
                        "media": {
                            "payload": payload_b64,
                            "timestamp": self._exotel_timestamp_ms(stream_sid),
                            "chunk": chunk_id
                        }
                    }
                    await exotel_ws.send_text(json.dumps(media_message))
                    logger.info(f"📤 EXOTEL MEDIA SENT: sid={stream_sid} seq={seq} chunk={chunk_id} bytes={len(chunk)} ts={media_message['media']['timestamp']}")
                    await self._send_mark_to_exotel(stream_sid, "playback_chunk")
                    # Track "bot is currently speaking" window for barge-in detection (inbound VAD).
                    try:
                        conn["bot_speaking_until"] = max(
                            float(conn.get("bot_speaking_until", 0.0) or 0.0),
                            asyncio.get_running_loop().time() + max(chunk_duration_s, 0.1) + 0.2,
                        )
                    except Exception:
                        pass
                    # Metrics: first bot audio out to Exotel (model audio path).
                    try:
                        m = conn.get("metrics") or {}
                        if m.get("first_gemini_audio_in_at") and not m.get("first_bot_audio_out_to_exotel_at"):
                            m["first_bot_audio_out_to_exotel_at"] = datetime.now()
                            conn["metrics"] = m
                            conn["first_bot_audio_out_mono"] = asyncio.get_running_loop().time()
                            logger.info(f"⏱️ METRIC first_bot_audio_out_to_exotel_at for {stream_sid}")
                    except Exception:
                        pass
                conn["last_audio_sent_at"] = datetime.now()

        except Exception as e:
            logger.error(f"❌ Error sending audio to Exotel: {e}")

    async def handle_exotel_mark(self, stream_sid: str, data: Dict):
        """Handle enhanced Exotel mark event"""
        mark_name = data.get("mark", {}).get("name", "unknown")
        timestamp = data.get("mark", {}).get("timestamp", "")

        logger.info(f"📍 EXOTEL MARK: {mark_name} @ {timestamp} for {stream_sid}")

        # Interruption: Exotel may send clear as a mark (name "clear" or "interrupt") instead of event "clear".
        if mark_name in ("clear", "interrupt"):
            await self.handle_exotel_clear(stream_sid, data)
            return

        # Enhanced mark event handling
        if self.exotel_enhanced_events:
            if mark_name == "speech_boundary":
                logger.info(f"🎯 SPEECH BOUNDARY DETECTED for {stream_sid}")
                if stream_sid in self.gemini_connections:
                    await self._commit_audio_buffer(stream_sid)

            elif mark_name == "audio_complete":
                logger.info(f"✅ AUDIO PLAYBACK COMPLETED for {stream_sid}")
            elif mark_name == "response_start":
                logger.info(f"🎯 AI RESPONSE PLAYBACK STARTED for {stream_sid}")

    async def handle_exotel_clear(self, stream_sid: str, data: Dict):
        """Handle Exotel clear event (user interrupted bot). Stops bot playback immediately for natural conversation.
        Called for event='clear' or mark name 'clear'/'interrupt'. Flushes current user audio to Gemini so Gemini hears the interruption and stops."""
        if stream_sid == "unknown":
            return
        logger.info(f"🧹 EXOTEL CLEAR - INTERRUPTING BOT SPEECH: {stream_sid}")

        try:
            # Flush current inbound buffer to Gemini so Gemini hears "stop" and can interrupt (START_OF_ACTIVITY_INTERRUPTS).
            # If we clear the buffer without sending, Gemini never gets the user's interruption and keeps generating.
            gemini_rate = 16000
            remainder = b""
            lock = self.audio_locks.get(stream_sid)
            if lock:
                async with lock:
                    remainder = self.audio_buffers.get(stream_sid, b"")
                    self.audio_buffers[stream_sid] = b""
            else:
                remainder = self.audio_buffers.get(stream_sid, b"")
                self.audio_buffers[stream_sid] = b""
            if remainder and stream_sid in self.gemini_connections:
                try:
                    ws = self.gemini_connections[stream_sid].get("websocket")
                    if ws and ws.state == State.OPEN:
                        await self._send_audio_to_gemini(stream_sid, remainder, gemini_rate)
                        logger.info(f"📤 Flush to Gemini on clear: {stream_sid} bytes={len(remainder)} (so Gemini hears interruption)")
                except Exception as e:
                    logger.warning(f"Failed to flush to Gemini on clear: {e}")

            # Reset rate conversion state to avoid audio artifacts after interruption
            self.ratecv_states[stream_sid] = None
            
            # Clear output jitter buffer and reset state
            if stream_sid in self.output_buffers:
                self.output_buffers[stream_sid] = []
            if stream_sid in self.output_buffer_started:
                self.output_buffer_started[stream_sid] = False

            # Drop any queued outbound audio to Exotel (bot playback) and suppress new bot audio for 1s.
            # This makes interruption feel immediate and natural (user speaks, bot stops).
            if stream_sid in self.exotel_out_pcm_buffers:
                self.exotel_out_pcm_buffers[stream_sid] = b""
            if stream_sid in self.exotel_connections:
                conn = self.exotel_connections[stream_sid]
                now_m = asyncio.get_running_loop().time()
                conn["next_exotel_send_at"] = now_m
                conn["drop_outgoing_until"] = now_m + 1.0  # 1s suppression so no trailing bot audio
                conn["bot_speaking_until"] = 0  # Reset so next user speech isn't treated as barge-in against old window
            
        except Exception as e:
            logger.error(f"❌ Error handling clear event: {e}")

    async def _handle_exotel_dtmf(self, stream_sid: str, data: Dict):
        """Handle DTMF (key press) from Exotel. Bidirectional streaming only. Log by default; extend to forward to Gemini if needed."""
        dtmf = data.get("dtmf", {})
        digit = dtmf.get("digit", "")
        duration = dtmf.get("duration", "")
        logger.info(f"📟 EXOTEL DTMF: {stream_sid} digit={digit!r} duration={duration!r}")

    async def handle_exotel_stop(self, stream_sid: str, data: Dict):
        """Handle Exotel stop event (stream stopped or call ended)."""
        sample_rate = self.connection_sample_rates.get(stream_sid, self.default_sample_rate)
        stop_info = data.get("stop", {})
        reason = stop_info.get("reason", "")
        logger.info(f"🛑 CALL ENDED: {stream_sid} @ {sample_rate}Hz reason={reason!r}")
    
    async def _commit_audio_buffer(self, stream_sid: str):
        if stream_sid not in self.audio_buffers:
            return
    
        buffer = self.audio_buffers[stream_sid]
        if len(buffer) > 0:
            # `audio_buffers` stores audio AFTER we resample Exotel input to 16kHz for Gemini.
            # Always compute sizes and label mimeType using Gemini's 16kHz rate.
            gemini_rate = 16000
            min_chunk_bytes = Config.get_chunk_size_bytes(gemini_rate, self.min_chunk_size_ms)

            if len(buffer) >= min_chunk_bytes:
                await self._send_audio_to_gemini(stream_sid, buffer, gemini_rate)
                self.audio_buffers[stream_sid] = b""
                logger.info(f"📤 COMMITTED REMAINING BUFFER: {len(buffer)} bytes for {stream_sid}")
        

    def _validate_connection_health(self, stream_sid: str) -> dict:
        """Validate and return connection health status"""
        
        # Check Gemini WebSocket state
        gemini_state = "CLOSED"
        if stream_sid in self.gemini_connections:
            ws = self.gemini_connections[stream_sid].get("websocket")
            if ws:
                gemini_state = ws.state.name

        # Check response handler task
        response_handler_running = False
        if stream_sid in self.response_handler_tasks:
            task = self.response_handler_tasks[stream_sid]
            response_handler_running = not task.done()

        health = {
            "stream_sid": stream_sid,
            "exotel_connected": stream_sid in self.exotel_connections,
            "gemini_connected": stream_sid in self.gemini_connections,
            "gemini_state": gemini_state,
            "response_handler_running": response_handler_running,
            "audio_buffer_size": len(self.audio_buffers.get(stream_sid, b"")),
            "reconnection_attempts": self.reconnection_attempts.get(stream_sid, 0)
        }
        return health
        
    
    async def _delayed_hangup(self, stream_sid: str, reason: str, delay: int = 2):
        """Initiate hangup after a delay to allow final messages to be sent"""
        try:
            await asyncio.sleep(delay)
            await self._initiate_hangup(stream_sid, reason)
        except Exception as e:
            logger.error(f"❌ Error in delayed hangup: {e}")
    
    async def _initiate_hangup(self, stream_sid: str, reason: str):
        """Initiate graceful hangup of the call"""
        try:
            if stream_sid not in self.exotel_connections:
                return
            
            connection = self.exotel_connections[stream_sid]
            if connection.get("hangup_initiated"):
                return 
            
            connection["hangup_initiated"] = True
            logger.info(f"📞 INITIATING GRACEFUL HANGUP for {stream_sid} - Reason: {reason}")
            
            
            # Send farewell message through Gemini
            if stream_sid in self.gemini_connections:
                try:
                    farewell_msg = {
                        "clientContent": {
                            "turns": [{"role": "user", "parts": [{"text": "The user said goodbye. Please give a warm, final farewell and end the call."}]}],
                            "turnComplete": True
                        }
                    }
                    await self.gemini_connections[stream_sid]["websocket"].send(json.dumps(farewell_msg))
                    logger.info(f"👋 SENT FAREWELL MESSAGE for {stream_sid}")
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.error(f"❌ Error sending farewell message: {e}")
            
            # Close Exotel connection (per Exotel doc: no explicit Stop from bot; closing WSS ends the stream)
            if stream_sid in self.exotel_connections:
                try:
                    await connection["websocket"].close()
                    logger.info(f"🛑 CLOSED EXOTEL WEBSOCKET for {stream_sid}")
                except Exception as e:
                    logger.error(f"❌ Error closing Exotel connection: {e}")
            
            if self.redis:
                await self.redis.delete(f"sales-agent:gemini:session_handle:{stream_sid}")
            await self.cleanup_connections(stream_sid)
            logger.info(f"✅ GRACEFUL HANGUP COMPLETED for {stream_sid}")
            
        except Exception as e:
            logger.error(f"❌ Error during graceful hangup: {e}")
    
    async def _monitor_connection_health(self, stream_sid: str):
        """Periodically check connection health; only trigger reconnection when Gemini WS is actually not OPEN."""
        try:
            check_interval = getattr(Config, "EXOTEL_HEALTH_CHECK_INTERVAL_SECONDS", 120)
            if check_interval <= 0:
                check_interval = 120
            consecutive_issues = 0

            while stream_sid in self.exotel_connections:
                await asyncio.sleep(check_interval)

                if stream_sid not in self.exotel_connections:
                    break

                # Skip if hangup initiated
                if self.exotel_connections[stream_sid].get("hangup_initiated"):
                    break

                health = self._validate_connection_health(stream_sid)
                issues = []

                if not health["gemini_connected"]:
                    issues.append("Gemini disconnected")
                elif health.get("gemini_state") != "OPEN":
                    issues.append(f"Gemini state: {health.get('gemini_state')}")

                # Log only; do not trigger reconnection for these
                if not health["response_handler_running"]:
                    issues.append("Response handler not running")
                if health["audio_buffer_size"] > 100000:
                    issues.append(f"Large audio buffer: {health['audio_buffer_size']} bytes")

                # Only treat actual Gemini disconnect as reconnection-triggering
                gemini_dead = not health["gemini_connected"] or health.get("gemini_state") != "OPEN"
                if gemini_dead:
                    consecutive_issues += 1
                    logger.warning(f"⚠️ Connection health issues for {stream_sid}: {', '.join(issues)}")
                    logger.warning(f"🏥 Full health status: {json.dumps(health, indent=2)}")

                    if consecutive_issues >= 2:
                        logger.error(f"❌ Persistent Gemini disconnect for {stream_sid}, triggering reconnection")
                        await self._handle_gemini_disconnection(stream_sid)
                        break
                else:
                    consecutive_issues = 0
                    if issues:
                        logger.debug(f"🏥 Health note for {stream_sid}: {', '.join(issues)}")
                    else:
                        logger.debug(f"✅ Connection health OK for {stream_sid}")
                    
        except Exception as e:
            logger.error(f"❌ Error monitoring connection health: {e}")
    
    async def _monitor_call_duration(self, stream_sid: str):
        """Continuously monitor call duration and hangup after 20 minutes"""
        try:
            while stream_sid in self.exotel_connections:
                # Check every 30 seconds
                await asyncio.sleep(30)
                
                if stream_sid not in self.exotel_connections:
                    break
                
                # Check if hangup already initiated
                if self.exotel_connections[stream_sid].get("hangup_initiated"):
                    break
                
                call_start_time = self.exotel_connections[stream_sid].get("call_start_time")
                if not call_start_time:
                    continue
                
                elapsed_time = datetime.now() - call_start_time
                max_duration = timedelta(seconds=Config.CALL_TIMEOUT_SECONDS)
                
                if elapsed_time >= max_duration:
                    logger.warning(f"⏰ CALL DURATION EXCEEDED 20 MINUTES for {stream_sid}")
                    await self._initiate_hangup(stream_sid, "call_duration_exceeded")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error monitoring call duration: {e}")
    
    async def _detect_conversation_ending(self, text: str) -> bool:
            # Common conversation ending phrases (in English and Hindi)
            ending_phrases = [
                "goodbye", "bye", "bye bye", "thank you bye", "that's all",
                "i have to go", "talk later", "धन्यवाद", "शुक्रिया", "अलविदा", 
                "बाय", "बस इतना ही", "ठीक है बाय", "ok bye", "theek hai bye"
            ]
            
            text_lower = text.lower().strip()
            return any(phrase in text_lower for phrase in ending_phrases)
    
    async def cleanup_connections(self, stream_sid: str):
        """Enhanced cleanup of both Exotel and Gemini connections"""
        try:
            if stream_sid in self.exotel_connections:
                self.exotel_connections[stream_sid]["cleanup_in_progress"] = True
                
            task = self.response_handler_tasks.pop(stream_sid, None)
            if task:
                task.cancel()
            silence_task = self.silence_gap_tasks.pop(stream_sid, None)
            if silence_task:
                silence_task.cancel()
            
            # Close Gemini connection
            gemini = self.gemini_connections.pop(stream_sid, None)
            if gemini:
                try: await gemini["websocket"].close()
                except: pass

            # Close and remove Exotel connection
            exotel = self.exotel_connections.pop(stream_sid, None)
            if exotel:
                try: await exotel["websocket"].close()
                except: pass

            # Wipe local states
            self.audio_buffers.pop(stream_sid, None)
            self.connection_sample_rates.pop(stream_sid, None)
            self.connection_chunk_sizes.pop(stream_sid, None)
            self.reconnection_attempts.pop(stream_sid, None)
            self.exotel_out_pcm_buffers.pop(stream_sid, None)
            self.exotel_send_locks.pop(stream_sid, None)
            # Cancel background monitor tasks.
            tasks = self.monitor_tasks.pop(stream_sid, None) or {}
            for t in tasks.values():
                try:
                    if t and not t.done():
                        t.cancel()
                except Exception:
                    pass

            # Emit metrics summary once (best-effort).
            try:
                if stream_sid in self.exotel_connections:
                    conn = self.exotel_connections[stream_sid]
                else:
                    conn = exotel or {}
                m = (conn.get("metrics") or {}) if isinstance(conn, dict) else {}
                if m and not (conn.get("metrics_logged") if isinstance(conn, dict) else False):
                    a = m.get("first_exotel_media_in_at")
                    d = m.get("first_audio_sent_to_gemini_at")
                    b = m.get("first_gemini_audio_in_at")
                    c = m.get("first_bot_audio_out_to_exotel_at")
                    def _ms(x, y):
                        if not x or not y:
                            return None
                        return int((y - x).total_seconds() * 1000)
                    logger.info(
                        "⏱️ ROUNDTRIP METRICS sid=%s exotel_in→gemini_send=%sms exotel_in→gemini_audio=%sms exotel_in→bot_out=%sms",
                        stream_sid,
                        _ms(a, d),
                        _ms(a, b),
                        _ms(a, c),
                    )
                    if isinstance(conn, dict):
                        conn["metrics_logged"] = True
            except Exception:
                pass
            
            # Clean up audio streaming state
            self.ratecv_states.pop(stream_sid, None)
            self.exotel_to_gemini_ratecv_states.pop(stream_sid, None)
            self.audio_locks.pop(stream_sid, None)
            self.output_buffers.pop(stream_sid, None)
            self.output_buffer_started.pop(stream_sid, None)
            
            logger.info(f"🧹 Successfully cleaned up all state for {stream_sid}")

        except Exception as e:
            logger.info(f"🧹 Error cleaning up connections: {e}")

    async def send_initial_greeting(self, stream_sid):
        try:
            gemini_ws = self.gemini_connections[stream_sid]["websocket"]
            
            # Get customer name for personalized greeting
            customer_name = None
            if stream_sid in self.exotel_connections:
                customer_name = self.exotel_connections[stream_sid].get("customer_name")
            
            # Use personalized greeting prompt
            greeting_prompt = Config.get_personalized_greeting_prompt(customer_name)
            
            greeting_message = {
                "clientContent": {
                    "turns":[
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": greeting_prompt
                                }
                            ]
                        }
                    ],
                    "turnComplete": True
                }
            }
            await gemini_ws.send(json.dumps(greeting_message))
            logger.info(f"📢 Sent personalized greeting for customer: {customer_name}")
        except Exception as e:
            logger.error(f"❌ Error sending initial greeting: {e}")

    def apply_noise_suppression(self, audio_data: bytes, sample_rate: int) -> bytes:
        """Enhanced noise suppression with sample rate awareness"""
        if not Config.AUDIO_ENHANCEMENT_ENABLED:
            return audio_data

        try:
            import numpy as np

            # Convert to 16-bit signed integers
            audio_samples = np.frombuffer(audio_data, dtype=np.int16).copy()

            # Enhanced noise gate with sample rate adjustment
            noise_threshold = Config.NOISE_THRESHOLD * (sample_rate / 8000)
            audio_samples = np.where(np.abs(audio_samples) < noise_threshold, 0, audio_samples)

            # Sample rate specific filtering
            if len(audio_samples) > 10:
                if sample_rate >= 24000:
                    window_size = min(7, len(audio_samples) // 2)
                elif sample_rate >= 16000:
                    window_size = min(5, len(audio_samples) // 2)
                else:
                    window_size = min(3, len(audio_samples) // 2)

                # High-pass filter
                moving_avg = np.convolve(audio_samples.astype(np.float32),
                                       np.ones(window_size)/window_size, mode='same')
                audio_samples = audio_samples - moving_avg.astype(np.int16) * 0.15

            # Dynamic range compression
            max_val = np.max(np.abs(audio_samples))
            if max_val > 0:
                compression_ratio = 0.85 if sample_rate >= 16000 else 0.8
                normalized = audio_samples.astype(np.float32) / max_val
                compressed = np.sign(normalized) * (np.abs(normalized) ** compression_ratio)
                audio_samples = (compressed * max_val * 0.9).astype(np.int16)

            return audio_samples.tobytes()

        except ImportError:
            logger.warning("⚠️ NumPy not available - skipping noise suppression")
            return audio_data
        except Exception as e:
            logger.error(f"❌ Error in noise suppression: {e}")
            return audio_data

    def pcm_to_ulaw(self, pcm_data: bytes) -> bytes:
        """Convert 16-bit PCM to G.711 u-law"""
        samples_pcm = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
        ulaw_bytes = []

        for sample in samples_pcm:
            # Clamp to 14-bit range
            sample = max(-8159, min(8159, sample))

            # Sign and magnitude
            if sample < 0:
                sample = -sample
                sign = 0x80
            else:
                sign = 0x00

            # Find the segment
            if sample < 32:
                segment = 0
                quantized = sample >> 1
            elif sample < 96:
                segment = 1
                quantized = (sample - 32) >> 2
            elif sample < 224:
                segment = 2
                quantized = (sample - 96) >> 3
            elif sample < 480:
                segment = 3
                quantized = (sample - 224) >> 4
            elif sample < 992:
                segment = 4
                quantized = (sample - 480) >> 5
            elif sample < 2016:
                segment = 5
                quantized = (sample - 992) >> 6
            elif sample < 4064:
                segment = 6
                quantized = (sample - 2016) >> 7
            else:
                segment = 7
                quantized = (sample - 4064) >> 8

            # Combine sign, segment, and quantized value
            ulaw_value = sign | (segment << 4) | quantized
            ulaw_bytes.append(ulaw_value ^ 0xFF)

        return bytes(ulaw_bytes)

    def ulaw_to_pcm(self, ulaw_data: bytes) -> bytes:
        """Convert G.711 u-law to 16-bit PCM"""
        pcm_samples = []

        for ulaw_byte in ulaw_data:
            ulaw_byte ^= 0xFF

            sign = ulaw_byte & 0x80
            segment = (ulaw_byte >> 4) & 0x07
            quantized = ulaw_byte & 0x0F

            # Decode based on segment
            if segment == 0:
                pcm_val = (quantized << 1) + 1
            elif segment == 1:
                pcm_val = ((quantized << 2) + 33)
            elif segment == 2:
                pcm_val = ((quantized << 3) + 97)
            elif segment == 3:
                pcm_val = ((quantized << 4) + 225)
            elif segment == 4:
                pcm_val = ((quantized << 5) + 481)
            elif segment == 5:
                pcm_val = ((quantized << 6) + 993)
            elif segment == 6:
                pcm_val = ((quantized << 7) + 2017)
            else:
                pcm_val = ((quantized << 8) + 4065)

            # Apply sign
            if sign:
                pcm_val = -pcm_val

            pcm_samples.append(pcm_val)

        return struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)

    def generate_test_tone(self, duration_ms: int = 200, frequency: int = 800, sample_rate: int = None) -> bytes:
        """Generate enhanced test tone with configurable sample rate"""
        import math

        if sample_rate is None:
            sample_rate = self.default_sample_rate

        samples = int(sample_rate * duration_ms / 1000)
        amplitude = 5000  # Moderate volume

        audio_data = []
        for i in range(samples):
            # Generate sine wave
            t = i / sample_rate
            sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
            sample = max(-32767, min(32767, sample))  # Clamp to 16-bit range
            audio_data.append(sample)

        # Convert to 16-bit PCM bytes (little-endian)
        return struct.pack(f'<{len(audio_data)}h', *audio_data)

    