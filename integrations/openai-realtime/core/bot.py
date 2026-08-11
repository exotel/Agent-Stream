#!/usr/bin/env python3
"""
OpenAI Realtime ↔ Exotel AgentStream bridge (sample).

Live entry via ``main.py`` / ``core.bot``. Not a multi-tenant production worker.
"""

import asyncio
import websockets
import json
import logging
import base64
import time
import struct
import ssl
import os
import re
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import Config

# Configure enhanced logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

class OpenAIRealtimeSalesBot:
    def __init__(self):
        # Validate configuration first
        Config.validate()
        
        self.exotel_connections: Dict[str, Dict[str, Any]] = {}

        self.openai_connections: Dict[str, Any] = {}
        
        # Enhanced audio buffering with dynamic sample rate support
        self.audio_buffers: Dict[str, bytes] = {}
        # OpenAI → Exotel paced playback (accumulate then emit telephony frames)
        self.outbound_buffers: Dict[str, bytearray] = {}  # PCM16 @ Exotel rate
        self.outbound_pcm24: Dict[str, bytearray] = {}  # PCM16 @ OpenAI wire rate
        self.outbound_ratecv_state: Dict[str, Any] = {}  # audioop.ratecv state
        self.inbound_ratecv_state: Dict[str, Any] = {}
        self.outbound_seq: Dict[str, int] = {}
        self.outbound_drain_tasks: Dict[str, asyncio.Task] = {}
        self.outbound_flush: Dict[str, bool] = {}
        self.bot_speaking: Dict[str, bool] = {}
        self.instant_greeting_sent: Dict[str, bool] = {}
        self._openai_connecting: set = set()
        self.connection_sample_rates: Dict[str, int] = {}  # Track sample rate per connection
        self.connection_chunk_sizes: Dict[str, int] = {}   # Track chunk size per connection
        # Pre-cached Exotel-rate PCM greeting (nodejs INSTANT_GREETING pattern)
        self.cached_greeting_pcm: Optional[bytes] = None
        
        # Default audio configuration (will be updated per connection)
        self.default_sample_rate = Config.DEFAULT_SAMPLE_RATE
        self.min_chunk_size_ms = Config.MIN_CHUNK_SIZE_MS
        self.buffer_size_ms = Config.BUFFER_SIZE_MS
        
        # OpenAI Configuration - SECURE: Load from environment variables
        self.openai_api_key = Config.OPENAI_API_KEY
        self.openai_model = Config.OPENAI_MODEL
        self.openai_voice = Config.OPENAI_VOICE
        
        # Enhanced features flags
        self.exotel_enhanced_events = Config.EXOTEL_MARK_CLEAR_ENHANCED
        self.variable_chunk_support = Config.EXOTEL_VARIABLE_CHUNK_SUPPORT
        self.dynamic_chunk_sizing = Config.DYNAMIC_CHUNK_SIZING
        self.half_duplex = Config.HALF_DUPLEX
        
        logger.info("🤖 OpenAI Realtime ↔ Exotel bridge initialized (speech-to-speech)")
        logger.info(f"🎵 Exotel rates: {Config.SUPPORTED_SAMPLE_RATES} Hz | OpenAI wire: {Config.OPENAI_PCM_RATE} Hz PCM")
        logger.info(
            f"📤 Outbound frame: {Config.EXOTEL_OUTBOUND_FRAME_MS}ms | "
            f"resample block: {Config.OPENAI_RESAMPLE_BLOCK_MS}ms | "
            f"pace={Config.OUTBOUND_PACE_FACTOR} | half_duplex={self.half_duplex}"
        )
        logger.info(
            f"⚡ Instant greeting: {Config.INSTANT_GREETING} | "
            f"VAD thr={Config.VAD_THRESHOLD} silence={Config.VAD_SILENCE_DURATION_MS}ms"
        )
        logger.info(f"🔊 Test tone on connect: {Config.SEND_TEST_TONE}")
        logger.info(f"🏢 Company: {Config.COMPANY_NAME} | Bot: {Config.SALES_BOT_NAME}")

    async def handle_exotel_websocket(self, websocket, path=None):
        """Handle incoming WebSocket connection from Exotel with enhanced sample rate detection"""
        stream_id = "unknown"
        
        try:
            # Extract sample rate from WebSocket path if available
            # Handle different websockets versions - path might be in websocket.path or passed as parameter
            try:
                websocket_path = path or getattr(websocket, 'path', '/')
            except:
                websocket_path = '/'
            detected_sample_rate = self.default_sample_rate  # Use default sample rate
            try:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(websocket_path).query)
                raw = (qs.get("sample-rate") or qs.get("sample_rate") or [None])[0]
                if raw is not None:
                    rate = int(str(raw).replace("Hz", "").replace("hz", "").strip())
                    if rate in Config.SUPPORTED_SAMPLE_RATES:
                        detected_sample_rate = rate
            except Exception:
                pass
            logger.info(f"📞 NEW ENHANCED SALES CALL from Exotel: {websocket.remote_address}")
            logger.info(f"🎵 Detected sample rate: {detected_sample_rate}Hz (path={websocket_path})")
            
            # Set up connection keep-alive and error handling
            async for message in websocket:
                try:
                    data = json.loads(message)
                    event = data.get("event", "")
                    # Never log full media payloads at INFO — floods the loop and delays TTS.
                    if event == "media":
                        logger.debug("📨 EXOTEL media frame")
                    else:
                        logger.info(f"📨 EXOTEL MESSAGE: {message[:500]}")
                    
                    # Extract stream ID
                    if "streamSid" in data:
                        stream_id = data["streamSid"]
                    elif "stream_sid" in data:
                        stream_id = data["stream_sid"]
                    
                    # Initialize connection settings on first event
                    if stream_id not in self.connection_sample_rates:
                        self._initialize_connection_settings(stream_id, detected_sample_rate, data)
                    
                    if event == "media":
                        logger.debug(f"🆔 STREAM ID: {stream_id} EVENT=media")
                    else:
                        logger.info(f"🆔 STREAM ID: {stream_id}")
                        logger.info(f"🎯 EVENT: '{event}' for {stream_id}")
                    
                    # Store enhanced Exotel connection
                    if stream_id not in self.exotel_connections:
                        self.exotel_connections[stream_id] = {
                            "websocket": websocket,
                            "start_time": time.time(),
                            "openai_connected": False,
                            "sample_rate": self.connection_sample_rates.get(stream_id, detected_sample_rate),
                            "chunk_size_bytes": self.connection_chunk_sizes.get(stream_id, 0),
                            "path": websocket_path
                        }
                        logger.info(f"📞 NEW ENHANCED CONNECTION: {stream_id} @ {self.connection_sample_rates[stream_id]}Hz")
                    
                    # Handle events with enhanced processing
                    if event == "connected":
                        await self.handle_exotel_connected(stream_id, data)
                    elif event == "start":
                        await self.handle_exotel_start(stream_id, data)
                    elif event == "media":
                        await self.handle_exotel_media(stream_id, data)
                    elif event == "mark":
                        await self.handle_exotel_mark(stream_id, data)
                    elif event == "clear":
                        await self.handle_exotel_clear(stream_id, data)
                    elif event == "stop":
                        await self.handle_exotel_stop(stream_id, data)
                        break  # Exit the message loop after stop event
                    else:
                        logger.info(f"🔄 UNHANDLED EVENT: {event} for {stream_id}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing Exotel message: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"🔚 EXOTEL CONNECTION CLOSED NORMALLY: {stream_id} (code: {e.code})")
        except Exception as e:
            logger.error(f"❌ Exotel WebSocket error: {e}")
        finally:
            logger.info(f"🧹 CLEANING UP ENHANCED CONNECTION: {stream_id}")
            await self.cleanup_connections(stream_id)

    def _initialize_connection_settings(self, stream_id: str, sample_rate: int, start_data: dict):
        """Initialize enhanced connection settings based on detected parameters"""
        self.connection_sample_rates[stream_id] = sample_rate
        self.bot_speaking[stream_id] = False
        self.outbound_seq[stream_id] = 0

        # Fixed inbound chunks → OpenAI (20ms default). Dynamic only if explicitly enabled.
        if self.dynamic_chunk_sizing:
            chunk_size_ms = Config.get_adaptive_chunk_size(sample_rate)
        else:
            chunk_size_ms = max(20, int(getattr(Config, "INBOUND_CHUNK_MS", 20)))

        chunk_size_bytes = Config.get_chunk_size_bytes(sample_rate, chunk_size_ms)
        # Align to even bytes (16-bit samples)
        chunk_size_bytes = max(2, chunk_size_bytes - (chunk_size_bytes % 2))
        self.connection_chunk_sizes[stream_id] = chunk_size_bytes

        logger.info(f"🔧 INITIALIZED CONNECTION {stream_id}:")
        logger.info(f"   📡 Sample Rate: {sample_rate}Hz (Exotel) ↔ {Config.OPENAI_PCM_RATE}Hz (OpenAI)")
        logger.info(f"   📥 Inbound chunk: {chunk_size_ms}ms ({chunk_size_bytes} bytes)")
        logger.info(f"   📤 Outbound frame: {Config.EXOTEL_OUTBOUND_FRAME_MS}ms")
        logger.info(f"   ⚙️ Enhanced Events: {self.exotel_enhanced_events}")

    async def handle_exotel_connected(self, stream_id: str, data: dict):
        """Handle Exotel connected event with enhanced confirmation"""
        logger.info(f"✅ EXOTEL CONNECTED (ENHANCED): {stream_id}")
        
        # Optional debug tone (SEND_TEST_TONE=true). Off by default — causes a beep before greeting.
        if Config.SEND_TEST_TONE:
            try:
                exotel_ws = self.exotel_connections[stream_id]["websocket"]
                sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
                
                test_tone = self.generate_test_tone(sample_rate=sample_rate)
                test_audio_b64 = base64.b64encode(test_tone).decode()
                
                test_message = {
                    "event": "media",
                    "streamSid": stream_id,
                    "media": {
                        "payload": test_audio_b64,
                        "timestamp": "0",
                        "sequenceNumber": "1",
                    },
                }
                
                await exotel_ws.send(json.dumps(test_message))
                logger.info(f"🔊 ENHANCED TEST TONE SENT ({sample_rate}Hz) to confirm audio pipeline for {stream_id}")
                
            except Exception as e:
                logger.error(f"❌ Error sending enhanced test tone: {e}")
        
        # Defer OpenAI connect to start (instant greeting + parallel connect there).
        logger.info("⏳ Waiting for Exotel start event before connecting OpenAI")


    async def handle_exotel_start(self, stream_id: str, data: dict):
        """Handle Exotel start: instant cached greeting + OpenAI connect in parallel (nodejs pattern)."""
        sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
        logger.info(f"🚀 ENHANCED SALES CALL STARTED: {stream_id} @ {sample_rate}Hz")

        if "mediaFormat" in data:
            media_format = data["mediaFormat"]
            logger.info(f"📺 Media Format: {json.dumps(media_format, indent=2)}")

        if stream_id == "unknown":
            return

        # INSTANT GREETING: play cached TTS before / while Realtime connects.
        if Config.INSTANT_GREETING and self.cached_greeting_pcm:
            # Mark before scheduling so Realtime session.update won't double-greet.
            self.instant_greeting_sent[stream_id] = True
            asyncio.create_task(self._play_instant_greeting(stream_id, sample_rate))
        elif Config.INSTANT_GREETING and not self.cached_greeting_pcm:
            logger.warning("⚡ Instant greeting enabled but cache empty — will use Realtime greeting")

        if stream_id not in self.openai_connections:
            # Background connect (do not block Exotel receive loop).
            asyncio.create_task(self.connect_to_openai_enhanced(stream_id))

    async def handle_exotel_media(self, stream_id: str, data: dict):
        """Forward Exotel mic PCM to OpenAI with fixed framing + stateful upsample."""

        # Optional half-duplex: skip mic while bot audio is on the wire.
        if self.half_duplex and self.bot_speaking.get(stream_id):
            return

        if stream_id not in self.openai_connections:
            if stream_id in self._openai_connecting:
                # Connect already in flight from start — don't spam reconnects.
                return
            logger.warning(f"⚠️ No OpenAI connection for {stream_id} - ESTABLISHING NOW")
            await self.connect_to_openai_enhanced(stream_id)
            await asyncio.sleep(0.1)
            if stream_id not in self.openai_connections:
                logger.error(f"❌ Failed to establish OpenAI connection for {stream_id}")
                return

        media = data.get("media", {})
        audio_payload = media.get("payload") or media.get("Payload") or ""
        if not audio_payload:
            return

        try:
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            target_chunk_bytes = self.connection_chunk_sizes.get(
                stream_id, Config.get_chunk_size_bytes(sample_rate, Config.INBOUND_CHUNK_MS)
            )

            exotel_pcm = base64.b64decode(audio_payload)
            if len(exotel_pcm) % 2:
                exotel_pcm = exotel_pcm[:-1]
            if not exotel_pcm:
                return

            # Passthrough by default — enhancement can muddy telephony audio.
            pcm = self.apply_noise_suppression(exotel_pcm, sample_rate)

            if stream_id not in self.audio_buffers:
                self.audio_buffers[stream_id] = b""
            self.audio_buffers[stream_id] += pcm

            if self.variable_chunk_support:
                await self._process_variable_chunks(stream_id, sample_rate)
            else:
                await self._process_fixed_chunks(stream_id, target_chunk_bytes, sample_rate)

        except Exception as e:
            logger.error(f"❌ Error processing Exotel media: {e}")

    async def _process_variable_chunks(self, stream_id: str, sample_rate: int):
        """Process audio with variable chunk sizes (Enhanced Exotel feature)"""
        min_chunk_bytes = Config.get_chunk_size_bytes(sample_rate, self.min_chunk_size_ms)
        max_chunk_bytes = Config.get_chunk_size_bytes(sample_rate, Config.MAX_CHUNK_SIZE_MS)
        
        buffer = self.audio_buffers[stream_id]
        
        # Process chunks of varying sizes
        while len(buffer) >= min_chunk_bytes:
            # Determine optimal chunk size dynamically
            optimal_chunk_size = min(len(buffer), max_chunk_bytes)
            
            # Extract chunk
            chunk = buffer[:optimal_chunk_size]
            self.audio_buffers[stream_id] = buffer[optimal_chunk_size:]
            buffer = self.audio_buffers[stream_id]
            
            # Send to OpenAI with enhanced format selection
            await self._send_audio_to_openai(stream_id, chunk, sample_rate)
            
            chunk_ms = (len(chunk) * 1000) // (sample_rate * 2)  # 16-bit PCM
            logger.debug(f"📤 VARIABLE CHUNK SENT: {len(chunk)} bytes ({chunk_ms}ms) @ {sample_rate}Hz")

    async def _process_fixed_chunks(self, stream_id: str, target_chunk_bytes: int, sample_rate: int):
        """Process audio with traditional fixed chunk sizes"""
        buffer = self.audio_buffers[stream_id]
        
        # Check if we have enough data for target chunk size
        if len(buffer) >= target_chunk_bytes:
            # Extract target chunk
            chunk = buffer[:target_chunk_bytes]
            self.audio_buffers[stream_id] = buffer[target_chunk_bytes:]
            
            # Send to OpenAI
            await self._send_audio_to_openai(stream_id, chunk, sample_rate)
            
            chunk_ms = (len(chunk) * 1000) // (sample_rate * 2)  # 16-bit PCM
            logger.debug(f"📤 FIXED CHUNK SENT: {len(chunk)} bytes ({chunk_ms}ms) @ {sample_rate}Hz")

    async def _send_audio_to_openai(self, stream_id: str, chunk: bytes, sample_rate: int):
        """Send audio chunk to OpenAI with enhanced format handling"""
        try:
            # Get OpenAI connection config
            openai_config = self.openai_connections[stream_id]
            input_format = openai_config.get("input_format", "pcm16")
            wire_hz = getattr(Config, "OPENAI_PCM_RATE", 24000)

            # Convert audio based on sample rate and format
            if input_format in ("pcm16", "audio/pcm"):
                # GA expects linear PCM @ 24 kHz; upsample from Exotel rate (stateful).
                openai_audio = chunk
                if sample_rate != wire_hz:
                    openai_audio = self._ratecv(
                        chunk,
                        sample_rate,
                        wire_hz,
                        stream_id,
                        self.inbound_ratecv_state,
                    )
            else:
                # Legacy G.711 u-law path (kept for compatibility)
                openai_audio = self.convert_pcm_to_ulaw(chunk)
            
            openai_audio_b64 = base64.b64encode(openai_audio).decode()
            
            # Send to OpenAI Realtime API
            openai_msg = {
                "type": "input_audio_buffer.append",
                "audio": openai_audio_b64
            }
            
            openai_ws = openai_config["websocket"]
            await openai_ws.send(json.dumps(openai_msg))
            
            logger.debug(f"📤 AUDIO SENT TO OPENAI: {len(chunk)} bytes PCM@{sample_rate} → {len(openai_audio)} bytes {input_format}")
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to OpenAI: {e}")

    async def handle_exotel_mark(self, stream_id: str, data: dict):
        """Handle enhanced Exotel mark event with improved synchronization"""
        mark_name = data.get("mark", {}).get("name", "unknown")
        timestamp = data.get("mark", {}).get("timestamp", "")
        
        logger.info(f"📍 ENHANCED EXOTEL MARK: {mark_name} @ {timestamp} for {stream_id}")
        
        # Enhanced mark event handling with Exotel's improved event system
        if self.exotel_enhanced_events:
            # New enhanced mark events support
            if mark_name == "speech_boundary":
                logger.info(f"🎯 SPEECH BOUNDARY DETECTED for {stream_id}")
                # Trigger response generation if customer finished speaking
                if stream_id in self.openai_connections:
                    await self._commit_audio_buffer(stream_id)
            elif mark_name == "audio_complete":
                logger.info(f"✅ AUDIO PLAYBACK COMPLETED for {stream_id}")
            elif mark_name == "response_start":
                logger.info(f"🎯 AI RESPONSE PLAYBACK STARTED for {stream_id}")
        
        # Legacy mark event support
        if mark_name == "greeting_complete":
            logger.info(f"✅ GREETING COMPLETED for {stream_id}")
        elif mark_name == "response_start":
            logger.info(f"🎯 RESPONSE PLAYBACK STARTED for {stream_id}")

    async def handle_exotel_clear(self, stream_id: str, data: dict):
        """Handle enhanced Exotel clear event with improved interruption support"""
        logger.info(f"🧹 ENHANCED EXOTEL CLEAR - INTERRUPTING BOT SPEECH: {stream_id}")
        
        if stream_id in self.openai_connections:
            try:
                openai_ws = self.openai_connections[stream_id]["websocket"]
                
                # Enhanced clear event handling
                if self.exotel_enhanced_events:
                    # 1. Cancel any ongoing response immediately
                    cancel_response_msg = {
                        "type": "response.cancel"
                    }
                    await openai_ws.send(json.dumps(cancel_response_msg))
                    logger.info(f"🛑 CANCELLED ONGOING RESPONSE (enhanced) for {stream_id}")
                    
                    # 2. Clear OpenAI's input audio buffer
                    clear_input_msg = {
                        "type": "input_audio_buffer.clear"
                    }
                    await openai_ws.send(json.dumps(clear_input_msg))
                    logger.info(f"🧹 CLEARED OPENAI INPUT BUFFER (enhanced) for {stream_id}")
                else:
                    # Legacy clear handling
                    clear_input_msg = {
                        "type": "input_audio_buffer.clear"
                    }
                    await openai_ws.send(json.dumps(clear_input_msg))
                    
                    cancel_response_msg = {
                        "type": "response.cancel"
                    }
                    await openai_ws.send(json.dumps(cancel_response_msg))
                
                # 3. Clear local inbound + outbound audio buffers
                if stream_id in self.audio_buffers:
                    self.audio_buffers[stream_id] = b""
                    logger.info(f"🧹 CLEARED LOCAL AUDIO BUFFER for {stream_id}")
                await self._clear_outbound(stream_id)
                
            except Exception as e:
                logger.error(f"❌ Error handling enhanced clear event: {e}")
        else:
            logger.warning(f"⚠️ No OpenAI connection to clear for {stream_id}")
            await self._clear_outbound(stream_id)

    async def _commit_audio_buffer(self, stream_id: str):
        """Commit any remaining audio in buffer to OpenAI (enhanced feature)"""
        if stream_id not in self.audio_buffers:
            return
            
        buffer = self.audio_buffers[stream_id]
        if len(buffer) > 0:
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            min_chunk_bytes = Config.get_chunk_size_bytes(sample_rate, self.min_chunk_size_ms)
            
            # Send remaining audio if it meets minimum size
            if len(buffer) >= min_chunk_bytes:
                await self._send_audio_to_openai(stream_id, buffer, sample_rate)
                self.audio_buffers[stream_id] = b""
                logger.info(f"📤 COMMITTED REMAINING BUFFER: {len(buffer)} bytes for {stream_id}")

    async def handle_exotel_stop(self, stream_id: str, data: dict):
        """Handle enhanced Exotel stop event"""
        sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
        logger.info(f"🛑 ENHANCED SALES CALL ENDED: {stream_id} @ {sample_rate}Hz")

    async def connect_to_openai_enhanced(self, stream_id: str):
        """Establish enhanced connection to OpenAI Realtime API with dynamic configuration"""
        if stream_id in self.openai_connections or stream_id in self._openai_connecting:
            return
        self._openai_connecting.add(stream_id)
        try:
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            logger.info(f"🔗 CONNECTING TO OPENAI (ENHANCED) for {stream_id} @ {sample_rate}Hz")
            
            # Enhanced URL for latest OpenAI Realtime API
            url = f"wss://api.openai.com/v1/realtime?model={self.openai_model}"
            
            # Create SSL context that handles certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # GA Realtime: Authorization only (OpenAI-Beta realtime=v1 is rejected)
            headers = [
                ("Authorization", f"Bearer {self.openai_api_key}"),
            ]
            
            # Connect to OpenAI Realtime API with enhanced SSL context
            # websockets 11.x uses extra_headers (additional_headers is 12+/13+)
            openai_ws = await websockets.connect(
                url, 
                extra_headers=headers,
                ssl=ssl_context,
                ping_interval=20,  # Enhanced connection stability
                ping_timeout=10
            )
            
            # Get enhanced session configuration
            session_config = Config.get_enhanced_session_config(sample_rate, self.openai_voice)
            wire_format = Config.get_wire_audio_format(sample_rate)
            
            self.openai_connections[stream_id] = {
                "websocket": openai_ws,
                "start_time": time.time(),
                "sample_rate": sample_rate,
                "input_format": wire_format,
                "output_format": wire_format,
                "session_config": session_config
            }
            
            # Update Exotel connection status
            if stream_id in self.exotel_connections:
                self.exotel_connections[stream_id]["openai_connected"] = True
            
            logger.info(f"✅ ENHANCED OPENAI CONNECTED for {stream_id} @ {sample_rate}Hz")
            in_fmt = session_config["audio"]["input"]["format"]["type"]
            out_fmt = session_config["audio"]["output"]["format"]["type"]
            logger.info(f"🎵 Audio Format: {in_fmt} → {out_fmt}")

            # Listen for events before session.update so we can wait for session.updated
            openai_connection = self.openai_connections[stream_id]
            openai_connection["session_ready"] = asyncio.Event()
            asyncio.create_task(self.handle_openai_responses_enhanced(stream_id, openai_ws))
            
            # Configure enhanced OpenAI session (waits for session.updated, then greets)
            await self.configure_openai_session_enhanced(stream_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI (enhanced): {e}")
            logger.error(f"Error type: {type(e).__name__}")
            if "SSL" in str(e):
                logger.error("💡 SSL Error - trying with insecure SSL context")
            elif "authentication" in str(e).lower():
                logger.error("💡 Authentication Error - check OpenAI API key")
            elif "websocket" in str(e).lower():
                logger.error("💡 WebSocket Error - check connection and headers")
            # Instant greeting may still be playing; allow mic after connect failure.
            if not self.instant_greeting_sent.get(stream_id):
                self.bot_speaking[stream_id] = False
        finally:
            self._openai_connecting.discard(stream_id)

    async def configure_openai_session_enhanced(self, stream_id: str):
        """Configure enhanced OpenAI Realtime session"""
        try:
            openai_connection = self.openai_connections[stream_id]
            openai_ws = openai_connection["websocket"]
            session_config = openai_connection["session_config"]
            sample_rate = openai_connection["sample_rate"]
            
            # Send enhanced session configuration
            session_update = {
                "type": "session.update",
                "session": session_config
            }
            
            await openai_ws.send(json.dumps(session_update))
            logger.info(f"🔧 ENHANCED OPENAI SESSION CONFIGURED for {stream_id}")
            logger.info(f"   🎵 Sample Rate: {sample_rate}Hz")
            logger.info(f"   🎤 Input Format: {session_config['audio']['input']['format']}")
            logger.info(f"   🔊 Output Format: {session_config['audio']['output']['format']}")
            logger.info(f"   🎭 Voice: {session_config['audio']['output'].get('voice')}")

            ready = openai_connection.get("session_ready")
            if ready is not None:
                try:
                    await asyncio.wait_for(ready.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ session.updated timeout for {stream_id}; sending greeting anyway")
            
            # Skip Realtime greeting only after instant greeting was actually queued.
            if self.instant_greeting_sent.get(stream_id):
                logger.info(f"⚡ Skipping Realtime greeting (instant cache) for {stream_id}")
                return

            await self.send_initial_greeting_enhanced(stream_id)
            
        except Exception as e:
            logger.error(f"❌ Error configuring enhanced OpenAI session: {e}")

    async def send_initial_greeting_enhanced(self, stream_id: str):
        """Fast path: one response.create (no extra conversation.item round-trip)."""
        try:
            openai_ws = self.openai_connections[stream_id]["websocket"]
            name = Config.SALES_BOT_NAME
            company = Config.COMPANY_NAME

            response_msg = {
                "type": "response.create",
                "response": {
                    "output_modalities": ["audio"],
                    "instructions": (
                        f"You are {name} from {company}. Greet the caller in one short "
                        "warm sentence and ask how you can help. Do not mention sample rates "
                        "or technical details. Do not repeat yourself."
                    ),
                },
            }
            await openai_ws.send(json.dumps(response_msg))
            logger.info(f"👋 ENHANCED INITIAL GREETING SENT for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending enhanced initial greeting: {e}")

    async def handle_openai_responses_enhanced(self, stream_id: str, openai_ws):
        """Handle enhanced responses from OpenAI Realtime API"""
        try:
            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type", "")
                    
                    logger.debug(f"🤖 ENHANCED OPENAI EVENT: {event_type} for {stream_id}")
                    
                    # GA: response.output_audio.delta; keep beta name for safety
                    if event_type in ("response.output_audio.delta", "response.audio.delta"):
                        await self.handle_openai_audio_delta_enhanced(stream_id, data)
                    elif event_type == "response.function_call_arguments.done":
                        await self.handle_openai_function_call_enhanced(stream_id, data)
                    elif event_type in (
                        "response.output_audio_transcript.delta",
                        "response.audio_transcript.delta",
                    ):
                        transcript_delta = data.get('delta', '')
                        if transcript_delta.strip():
                            logger.info(f"🗣️ SARAH SPEAKING: {transcript_delta}")
                    elif event_type == "input_audio_buffer.speech_started":
                        logger.info(f"🎤 CUSTOMER STARTED SPEAKING (enhanced) for {stream_id}")
                        # Enhanced interruption handling
                        await self._handle_customer_interruption(stream_id, openai_ws)
                    elif event_type == "input_audio_buffer.speech_stopped":
                        logger.info(f"🎤 CUSTOMER STOPPED SPEAKING (enhanced) for {stream_id}")
                        # GA server_vad with create_response=True already starts a response;
                        # do not call response.create again (causes conversation_already_has_active_response).
                    elif event_type in (
                        "response.output_audio.done",
                        "response.audio.done",
                    ):
                        # Flush as soon as audio stream ends (nodejs flushAudioBuffer).
                        await self._flush_outbound(stream_id)
                    elif event_type == "response.done":
                        logger.info(f"✅ SARAH FINISHED RESPONSE (enhanced) for {stream_id}")
                        await self._flush_outbound(stream_id)
                    elif event_type == "error":
                        err = data.get("error") or {}
                        # Benign race when cancel fires after response already ended
                        if err.get("code") == "response_cancel_not_active":
                            logger.debug(f"OpenAI cancel race (ignored): {err.get('message')}")
                        else:
                            logger.error(f"❌ ENHANCED OPENAI ERROR: {data}")
                    elif event_type == "session.updated":
                        logger.info(f"🔧 SESSION UPDATED for {stream_id}")
                        ready = self.openai_connections.get(stream_id, {}).get("session_ready")
                        if ready is not None and not ready.is_set():
                            ready.set()
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error from OpenAI (enhanced): {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing enhanced OpenAI response: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in enhanced OpenAI response handler: {e}")

    async def _handle_customer_interruption(self, stream_id: str, openai_ws):
        """Barge-in: clear Exotel playback + cancel OpenAI (nodejs BargeInHandler)."""
        try:
            await self._clear_outbound(stream_id)
            await self._send_exotel_clear(stream_id)
            cancel_response_msg = {
                "type": "response.cancel"
            }
            await openai_ws.send(json.dumps(cancel_response_msg))
            logger.info(f"🛑 ENHANCED BOT INTERRUPTED - Customer started speaking for {stream_id}")

        except Exception as e:
            logger.error(f"❌ Error handling enhanced customer interruption: {e}")

    async def _send_exotel_clear(self, stream_id: str) -> None:
        """Tell Exotel to drop unplayed bot audio (nodejs sender.sendClear)."""
        conn = self.exotel_connections.get(stream_id)
        if not conn:
            return
        try:
            await conn["websocket"].send(
                json.dumps({"event": "clear", "streamSid": stream_id})
            )
        except Exception as e:
            logger.debug(f"clear send failed for {stream_id}: {e}")

    async def trigger_openai_response_enhanced(self, stream_id: str, openai_ws):
        """Trigger enhanced OpenAI response generation with improved parameters"""
        try:
            # Enhanced response triggering with better configuration
            await asyncio.sleep(0.2)  # Optimized pause verification
            
            response_create = {
                "type": "response.create",
                "response": {
                    "output_modalities": ["audio"],
                    "instructions": "Respond naturally and conversationally. Use appropriate pauses and inflections.",
                }
            }
            await openai_ws.send(json.dumps(response_create))
            logger.info(f"🎯 TRIGGERED ENHANCED OPENAI RESPONSE for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error triggering enhanced OpenAI response: {e}")

    def _outbound_frame_bytes(self, sample_rate: int) -> int:
        """Exotel media frame size (~100ms → 3200 bytes @ 8 kHz; multiple of 320)."""
        ms = max(20, int(getattr(Config, "EXOTEL_OUTBOUND_FRAME_MS", 100)))
        frame = max(320, int(sample_rate * (ms / 1000.0) * 2))
        return max(320, (frame // 320) * 320)

    def _resample_block_bytes(self, rate: int) -> int:
        ms = max(20, int(getattr(Config, "OPENAI_RESAMPLE_BLOCK_MS", 100)))
        return max(2, int(rate * (ms / 1000.0) * 2) // 2 * 2)

    def _soft_limit_pcm16(self, pcm: bytes) -> bytes:
        """Prevent rare post-resample peaks that cause clicks/hiss on the phone."""
        if not pcm or len(pcm) < 2:
            return pcm
        if len(pcm) % 2:
            pcm = pcm[:-1]
        try:
            import array

            samples = array.array("h")
            samples.frombytes(pcm)
            peak = 0
            for s in samples:
                a = s if s >= 0 else -s
                if a > peak:
                    peak = a
            if peak <= 30000:
                return pcm
            scale = 28000.0 / peak
            for i, s in enumerate(samples):
                samples[i] = int(s * scale)
            return samples.tobytes()
        except Exception:
            return pcm

    def _ratecv(
        self,
        pcm: bytes,
        from_rate: int,
        to_rate: int,
        state_key: str,
        state_map: Dict[str, Any],
    ) -> bytes:
        """Stateful ratecv — avoids clicks/hiss from resetting filter each delta."""
        if from_rate == to_rate or not pcm:
            return pcm
        if len(pcm) % 2:
            pcm = pcm[:-1]
        if not pcm:
            return pcm
        try:
            import audioop

            converted, new_state = audioop.ratecv(
                pcm, 2, 1, from_rate, to_rate, state_map.get(state_key)
            )
            state_map[state_key] = new_state
            return self._soft_limit_pcm16(converted)
        except Exception as e:
            logger.warning(f"⚠️ ratecv failed ({e}); falling back")
            return self._soft_limit_pcm16(self._resample_audio(pcm, from_rate, to_rate))

    async def _clear_outbound(self, stream_id: str) -> None:
        """Drop queued outbound PCM and stop the drain task."""
        self.bot_speaking[stream_id] = False
        self.outbound_buffers[stream_id] = bytearray()
        self.outbound_pcm24[stream_id] = bytearray()
        self.outbound_ratecv_state.pop(stream_id, None)
        self.outbound_flush[stream_id] = False
        task = self.outbound_drain_tasks.pop(stream_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def _flush_outbound(self, stream_id: str) -> None:
        """Resample any remaining PCM24, then drain short Exotel tail."""
        wire_hz = getattr(Config, "OPENAI_PCM_RATE", 24000)
        sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
        pcm24 = self.outbound_pcm24.setdefault(stream_id, bytearray())
        if pcm24:
            converted = self._ratecv(
                bytes(pcm24),
                wire_hz,
                sample_rate,
                stream_id,
                self.outbound_ratecv_state,
            )
            pcm24.clear()
            if converted:
                self.outbound_buffers.setdefault(stream_id, bytearray()).extend(converted)
        self.outbound_flush[stream_id] = True
        self._ensure_outbound_drainer(stream_id)

    def _ensure_outbound_drainer(self, stream_id: str) -> None:
        task = self.outbound_drain_tasks.get(stream_id)
        if task is None or task.done():
            self.outbound_drain_tasks[stream_id] = asyncio.create_task(
                self._drain_outbound_to_exotel(stream_id)
            )

    async def _drain_outbound_to_exotel(self, stream_id: str) -> None:
        """Send OpenAI→Exotel frames ASAP (nodejs sendMedia) with optional light pacing."""
        clock = time.monotonic()
        frames_sent = 0
        pace = max(0.0, float(getattr(Config, "OUTBOUND_PACE_FACTOR", 0.0)))
        try:
            while stream_id in self.exotel_connections:
                sample_rate = self.connection_sample_rates.get(
                    stream_id, self.default_sample_rate
                )
                frame_bytes = self._outbound_frame_bytes(sample_rate)
                frame_sec = (frame_bytes / 2) / max(sample_rate, 1)
                buf = self.outbound_buffers.setdefault(stream_id, bytearray())
                flush = self.outbound_flush.get(stream_id, False)

                if len(buf) >= frame_bytes:
                    frame = bytes(buf[:frame_bytes])
                    del buf[:frame_bytes]
                    self.bot_speaking[stream_id] = True
                    await self._send_exotel_media_frame(stream_id, frame, sample_rate)
                    frames_sent += 1
                    if pace > 0:
                        target = clock + frames_sent * frame_sec * pace
                        delay = target - time.monotonic()
                        if delay > 0.001:
                            await asyncio.sleep(delay)
                        elif delay < -0.1:
                            clock = time.monotonic()
                            frames_sent = 0
                        else:
                            await asyncio.sleep(0)
                    else:
                        # Yield so Exotel receive loop stays responsive (no realtime wait).
                        await asyncio.sleep(0)
                    continue

                if flush and len(buf) >= 2:
                    # Pad to full MIN frame like nodejs flushAudioBuffer (3200 B).
                    frame = bytes(buf)
                    buf.clear()
                    self.outbound_flush[stream_id] = False
                    if len(frame) % 2:
                        frame = frame[:-1]
                    if frame and len(frame) < frame_bytes:
                        frame = frame + (b"\x00" * (frame_bytes - len(frame)))
                    elif frame and len(frame) % 320:
                        frame = frame + (b"\x00" * (320 - (len(frame) % 320)))
                    if frame:
                        self.bot_speaking[stream_id] = True
                        await self._send_exotel_media_frame(stream_id, frame, sample_rate)
                        if pace > 0:
                            await asyncio.sleep(frame_sec * pace)
                        else:
                            await asyncio.sleep(0)
                    self.bot_speaking[stream_id] = False
                    break

                if flush and len(buf) < 2:
                    self.outbound_flush[stream_id] = False
                    self.bot_speaking[stream_id] = False
                    break

                await asyncio.sleep(0.005)
        except asyncio.CancelledError:
            self.bot_speaking[stream_id] = False
            raise
        except Exception as e:
            logger.error(f"❌ Outbound drain error for {stream_id}: {e}")
            self.bot_speaking[stream_id] = False
        finally:
            current = self.outbound_drain_tasks.get(stream_id)
            if current is asyncio.current_task():
                self.outbound_drain_tasks.pop(stream_id, None)

    async def _send_exotel_media_frame(
        self, stream_id: str, pcm: bytes, sample_rate: int
    ) -> None:
        if stream_id not in self.exotel_connections or not pcm:
            return
        if len(pcm) % 2:
            pcm = pcm[:-1]
        if not pcm:
            return

        conn = self.exotel_connections[stream_id]
        exotel_ws = conn["websocket"]
        seq = self.outbound_seq.get(stream_id, 0) + 1
        self.outbound_seq[stream_id] = seq
        t0 = conn.get("start_time") or time.time()
        elapsed_ms = int((time.time() - t0) * 1000)

        if not conn.get("first_audio_logged"):
            logger.info(
                f"first_audio_ms={elapsed_ms} stream={stream_id} rate={sample_rate} "
                f"frame_bytes={len(pcm)}"
            )
            conn["first_audio_logged"] = True
            openai_conn = self.openai_connections.get(stream_id)
            if openai_conn is not None:
                openai_conn["first_audio_logged"] = True

        # Match shared AgentStream media_event: chunk + timestamp + sequenceNumber.
        media_message = {
            "event": "media",
            "streamSid": stream_id,
            "media": {
                "payload": base64.b64encode(pcm).decode("ascii"),
                "chunk": str(seq),
                "timestamp": str(elapsed_ms),
                "sequenceNumber": str(seq),
            },
        }
        await exotel_ws.send(json.dumps(media_message))
        logger.debug(
            f"📞 EXOTEL FRAME: {len(pcm)} bytes PCM @{sample_rate}Hz "
            f"seq={seq} ts={elapsed_ms}"
        )

    async def handle_openai_audio_delta_enhanced(self, stream_id: str, data: dict):
        """Queue OpenAI PCM24, stateful-resample in blocks, pace Exotel frames."""
        try:
            if stream_id not in self.exotel_connections:
                logger.warning(f"⚠️ No Exotel connection for {stream_id}")
                return

            audio_delta = data.get("delta", "")
            if not audio_delta:
                return

            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            openai_conn = self.openai_connections[stream_id]
            output_format = openai_conn.get("output_format", "pcm16")

            openai_audio = base64.b64decode(audio_delta)
            if not openai_audio:
                return

            wire_hz = getattr(Config, "OPENAI_PCM_RATE", 24000)

            if output_format in ("pcm16", "audio/pcm"):
                if len(openai_audio) % 2:
                    openai_audio = openai_audio[:-1]
                pcm24 = self.outbound_pcm24.setdefault(stream_id, bytearray())
                pcm24.extend(openai_audio)
                block = self._resample_block_bytes(wire_hz)
                out_buf = self.outbound_buffers.setdefault(stream_id, bytearray())
                while len(pcm24) >= block:
                    chunk = bytes(pcm24[:block])
                    del pcm24[:block]
                    out_buf.extend(
                        self._ratecv(
                            chunk,
                            wire_hz,
                            sample_rate,
                            stream_id,
                            self.outbound_ratecv_state,
                        )
                    )
            else:
                # Legacy μ-law @ 8 kHz
                pcm8 = self.convert_ulaw_to_pcm(openai_audio)
                if sample_rate != 8000:
                    pcm8 = self._ratecv(
                        pcm8, 8000, sample_rate, stream_id, self.outbound_ratecv_state
                    )
                self.outbound_buffers.setdefault(stream_id, bytearray()).extend(pcm8)

            self.outbound_flush[stream_id] = False
            self.bot_speaking[stream_id] = True
            self._ensure_outbound_drainer(stream_id)

        except Exception as e:
            logger.error(f"❌ Error queueing enhanced audio for Exotel: {e}")

    async def handle_openai_function_call_enhanced(self, stream_id: str, data: dict):
        """Handle enhanced function calls from OpenAI with improved error handling"""
        try:
            function_name = data.get("name", "")
            arguments = json.loads(data.get("arguments", "{}"))
            call_id = data.get("call_id", "")
            
            logger.info(f"🔧 ENHANCED FUNCTION CALL: {function_name} with {arguments}")
            
            # Execute function with enhanced error handling
            if function_name == "schedule_demo":
                result = await self.schedule_demo_enhanced(arguments)
            elif function_name == "send_pricing_info":
                result = await self.send_pricing_info_enhanced(arguments)
            elif function_name == "transfer_to_human":
                result = await self.transfer_to_human_enhanced(stream_id, arguments)
            else:
                result = {"status": "unknown_function", "error": f"Function {function_name} not implemented"}
            
            # Send enhanced function result back to OpenAI
            openai_ws = self.openai_connections[stream_id]["websocket"]
            
            function_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }
            
            await openai_ws.send(json.dumps(function_response))
            
            # Create enhanced response
            response_msg = {
                "type": "response.create",
                "response": {
                    "output_modalities": ["audio"],
                    "instructions": f"Based on the function result, provide a natural response to the customer about {function_name}."
                }
            }
            await openai_ws.send(json.dumps(response_msg))
            
            logger.info(f"✅ ENHANCED FUNCTION CALL COMPLETED: {function_name}")
            
        except Exception as e:
            logger.error(f"❌ Error handling enhanced function call: {e}")

    async def schedule_demo_enhanced(self, args: dict) -> dict:
        """Enhanced demo scheduling with better data capture"""
        logger.info(f"📅 SCHEDULING ENHANCED DEMO: {args}")
        
        # Extract enhanced information
        customer_name = args.get('customer_name', 'Customer')
        product_interest = args.get('product_interest', 'Our solutions')
        company = args.get('company', '')
        contact_info = {
            'email': args.get('contact_email', ''),
            'phone': args.get('contact_phone', '')
        }
        preferences = {
            'date': args.get('preferred_date', ''),
            'time': args.get('preferred_time', ''),
            'notes': args.get('additional_notes', '')
        }
        
        # In production, this would integrate with CRM/scheduling system
        return {
            "status": "success",
            "message": f"Demo scheduled for {customer_name} interested in {product_interest}",
            "demo_id": f"DEMO_{int(time.time())}",
            "customer_name": customer_name,
            "product_interest": product_interest,
            "company": company,
            "contact_info": contact_info,
            "preferences": preferences,
            "scheduled_at": time.strftime('%Y-%m-%d %H:%M:%S')
        }

    async def send_pricing_info_enhanced(self, args: dict) -> dict:
        """Enhanced pricing information with detailed breakdown"""
        logger.info(f"💰 SENDING ENHANCED PRICING INFO: {args}")
        
        product = args.get('product', 'Our solution')
        company_size = args.get('company_size', 'standard')
        contact_email = args.get('contact_email', '')
        custom_requirements = args.get('custom_requirements', '')
        
        # In production, this would calculate custom pricing
        return {
            "status": "success", 
            "message": f"Detailed pricing information for {product} will be sent to {contact_email}",
            "product": product,
            "company_size": company_size,
            "contact_email": contact_email,
            "custom_requirements": custom_requirements,
            "quote_id": f"QUOTE_{int(time.time())}",
            "estimated_delivery": "within 24 hours"
        }

    async def transfer_to_human_enhanced(self, stream_id: str, args: dict) -> dict:
        """Enhanced human transfer with context preservation"""
        logger.info(f"👥 TRANSFERRING TO HUMAN AGENT: {args}")
        
        reason = args.get('reason', 'Customer request')
        context = args.get('customer_context', 'No additional context')
        urgency = args.get('urgency', 'medium')
        
        # In production, this would interface with call center system
        transfer_result = {
            "status": "transfer_initiated",
            "message": f"Transferring to human agent - {reason}",
            "transfer_id": f"TRANSFER_{int(time.time())}",
            "reason": reason,
            "context": context,
            "urgency": urgency,
            "stream_id": stream_id,
            "estimated_wait": "2-3 minutes"
        }
        
        # Log for human agent context
        logger.info(f"🚨 HUMAN TRANSFER INITIATED for {stream_id}:")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Context: {context}")
        logger.info(f"   Urgency: {urgency}")
        
        return transfer_result

    def _resample_audio(self, audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample 16-bit mono PCM between sample rates (telephony-critical)."""
        if from_rate == to_rate or not audio_data:
            return audio_data
        if len(audio_data) % 2:
            audio_data = audio_data[:-1]
        if not audio_data:
            return audio_data

        # Prefer audioop (audioop-lts on Python 3.13+) — reliable and fast.
        try:
            import audioop

            converted, _ = audioop.ratecv(audio_data, 2, 1, from_rate, to_rate, None)
            logger.debug(f"🔄 RESAMPLED AUDIO: {from_rate}Hz → {to_rate}Hz ({len(audio_data)}→{len(converted)} B)")
            return converted
        except Exception as e:
            logger.warning(f"⚠️ audioop resample failed ({e}); trying numpy")

        try:
            import numpy as np

            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            n_out = max(1, int(round(len(samples) * to_rate / from_rate)))
            x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
            resampled = np.interp(x_new, x_old, samples)
            out = np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
            logger.debug(f"🔄 RESAMPLED AUDIO (numpy): {from_rate}Hz → {to_rate}Hz")
            return out
        except Exception as e:
            logger.error(f"❌ Error resampling audio: {e}")
            return audio_data

    def apply_noise_suppression(self, audio_data: bytes, sample_rate: int) -> bytes:
        """Enhanced noise suppression with sample rate awareness"""
        if not Config.AUDIO_ENHANCEMENT_ENABLED:
            return audio_data
            
        try:
            import numpy as np
            
            # Convert to 16-bit signed integers
            audio_samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Enhanced noise gate with sample rate adjustment
            noise_threshold = Config.NOISE_THRESHOLD * (sample_rate / 8000)  # Scale with sample rate
            audio_samples = np.where(np.abs(audio_samples) < noise_threshold, 0, audio_samples)
            
            # Sample rate specific filtering
            if len(audio_samples) > 10:
                # Adjust filter parameters based on sample rate
                if sample_rate >= 24000:
                    window_size = min(7, len(audio_samples) // 2)  # Larger window for higher sample rates
                elif sample_rate >= 16000:
                    window_size = min(5, len(audio_samples) // 2)
                else:
                    window_size = min(3, len(audio_samples) // 2)
                
                # Enhanced high-pass filter
                moving_avg = np.convolve(audio_samples.astype(np.float32), 
                                       np.ones(window_size)/window_size, mode='same')
                audio_samples = audio_samples - moving_avg.astype(np.int16) * 0.15
            
            # Enhanced dynamic range compression
            max_val = np.max(np.abs(audio_samples))
            if max_val > 0:
                # Adaptive compression based on sample rate
                compression_ratio = 0.85 if sample_rate >= 16000 else 0.8
                normalized = audio_samples.astype(np.float32) / max_val
                compressed = np.sign(normalized) * (np.abs(normalized) ** compression_ratio)
                audio_samples = (compressed * max_val * 0.9).astype(np.int16)
            
            return audio_samples.tobytes()
            
        except ImportError:
            logger.warning("📢 NumPy not available - skipping enhanced noise suppression")
            return audio_data
        except Exception as e:
            logger.error(f"❌ Error in enhanced noise suppression: {e}")
            return audio_data

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

    def convert_pcm_to_ulaw(self, pcm_data: bytes) -> bytes:
        """Convert 16-bit PCM to G.711 u-law (same sample rate)"""
        # G.711 u-law encoding table (simplified)
        samples_pcm = struct.unpack(f'<{len(pcm_data)//2}h', pcm_data)
        ulaw_bytes = []
        
        for sample in samples_pcm:
            # Simplified u-law encoding
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
            ulaw_bytes.append(ulaw_value ^ 0xFF)  # Complement for u-law
        
        return bytes(ulaw_bytes)

    def convert_ulaw_to_pcm(self, ulaw_data: bytes) -> bytes:
        """Convert G.711 u-law to 16-bit PCM (same sample rate)"""
        # G.711 u-law decoding table (simplified)
        pcm_samples = []
        
        for ulaw_byte in ulaw_data:
            ulaw_byte ^= 0xFF  # Un-complement
            
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
            else:  # segment == 7
                pcm_val = ((quantized << 8) + 4065)
            
            # Apply sign
            if sign:
                pcm_val = -pcm_val
            
            pcm_samples.append(pcm_val)
        
        return struct.pack(f'<{len(pcm_samples)}h', *pcm_samples)


    async def start_server(self):
        """Start the WebSocket server"""
        try:
            if Config.INSTANT_GREETING:
                await self._cache_greeting_pcm()

            logger.info(f'🚀 Starting Enhanced Sales Bot Server on {Config.SERVER_HOST}:{Config.SERVER_PORT}')
            logger.info('📞 Ready for Enhanced Exotel streaming connections!')
            logger.info(
                f'🎵 Outbound {Config.EXOTEL_OUTBOUND_FRAME_MS}ms frames | '
                f'pace={Config.OUTBOUND_PACE_FACTOR} | instant_greeting={bool(self.cached_greeting_pcm)}'
            )
            logger.info('✨ Enhanced mark/clear event handling')
            logger.info('🔐 Using secure environment-based configuration')
            
            # Start WebSocket server
            async with websockets.serve(
                self.handle_exotel_websocket,
                Config.SERVER_HOST,
                Config.SERVER_PORT
            ):
                logger.info(f'✅ Enhanced Sales Bot Server running at ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}')
                logger.info('🎯 Ready for enhanced calls with multi-sample rate support...')
                await asyncio.Future()  # Run forever
                
        except Exception as e:
            logger.error(f'❌ Enhanced Server Error: {e}')
            raise

    async def _cache_greeting_pcm(self) -> None:
        """Pre-cache OpenAI TTS greeting at Exotel rate (nodejs cacheGreeting)."""
        text = (Config.GREETING_TEXT or "").strip()
        if not text:
            return
        logger.info("⏳ Pre-caching greeting audio via OpenAI TTS...")
        t0 = time.time()
        try:
            pcm24 = await asyncio.to_thread(self._fetch_openai_tts_pcm, text)
            if not pcm24:
                logger.warning("⚠️ Greeting cache empty — Realtime greeting will be used")
                return
            # TTS pcm is 24 kHz mono; resample once to default Exotel rate.
            pcm8 = self._resample_audio(pcm24, Config.OPENAI_PCM_RATE, self.default_sample_rate)
            self.cached_greeting_pcm = pcm8
            logger.info(
                f"✅ Greeting cached in {int((time.time() - t0) * 1000)}ms "
                f"({len(pcm8)} bytes @ {self.default_sample_rate}Hz)"
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not pre-cache greeting: {e}")

    def _tts_voice_for_cache(self) -> str:
        """Map Realtime voice names to TTS-1 voices."""
        allowed = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        voice = (self.openai_voice or "alloy").lower()
        if voice in allowed:
            return voice
        # coral / sage / etc. → closest common TTS voice
        return "nova" if voice in {"coral", "shimmer", "verse"} else "alloy"

    def _fetch_openai_tts_pcm(self, text: str) -> bytes:
        """Sync OpenAI /v1/audio/speech → raw PCM24 (tts-1)."""
        import urllib.error
        import urllib.request

        body = json.dumps(
            {
                "model": "tts-1",
                # Realtime voices (e.g. coral) may not exist on TTS-1.
                "voice": self._tts_voice_for_cache(),
                "input": text,
                "response_format": "pcm",
                "speed": 1.0,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=body,
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"TTS HTTP {e.code}: {detail}") from e

    async def _play_instant_greeting(self, stream_id: str, sample_rate: int) -> None:
        """Burst-send cached greeting in Exotel min chunks (nodejs onStart)."""
        pcm = self.cached_greeting_pcm
        if not pcm or stream_id not in self.exotel_connections:
            return

        # If call sample rate differs from cache, resample once.
        if sample_rate != self.default_sample_rate:
            pcm = self._resample_audio(pcm, self.default_sample_rate, sample_rate)

        self.instant_greeting_sent[stream_id] = True
        self.bot_speaking[stream_id] = True
        t0 = time.time()
        frame = self._outbound_frame_bytes(sample_rate)
        offset = 0
        frames = 0
        try:
            while offset < len(pcm) and stream_id in self.exotel_connections:
                chunk = pcm[offset : offset + frame]
                offset += len(chunk)
                if len(chunk) < 2:
                    break
                if len(chunk) < frame:
                    chunk = chunk + (b"\x00" * (frame - len(chunk)))
                await self._send_exotel_media_frame(stream_id, chunk, sample_rate)
                frames += 1
                await asyncio.sleep(0)  # yield; no realtime wait (nodejs sendMedia)
            # Mark so Exotel can acknowledge playback boundary.
            await self._send_exotel_mark(stream_id, "greeting-complete")
            logger.info(
                f"⚡ INSTANT greeting sent in {int((time.time() - t0) * 1000)}ms "
                f"({frames} frames) for {stream_id}"
            )
        except Exception as e:
            logger.error(f"❌ Instant greeting failed for {stream_id}: {e}")
        finally:
            # Mic open after greeting dump; Realtime will set speaking again on deltas.
            self.bot_speaking[stream_id] = False

    async def _send_exotel_mark(self, stream_id: str, name: str) -> None:
        conn = self.exotel_connections.get(stream_id)
        if not conn:
            return
        try:
            await conn["websocket"].send(
                json.dumps(
                    {
                        "event": "mark",
                        "streamSid": stream_id,
                        "mark": {"name": name},
                    }
                )
            )
        except Exception as e:
            logger.debug(f"mark send failed for {stream_id}: {e}")

    async def handle_exotel_dtmf(self, message: Dict[str, Any], stream_id: str):
        """Handle DTMF events from Exotel"""
        try:
            dtmf_data = message.get('dtmf', {})
            digit = dtmf_data.get('digit', '')
            duration = dtmf_data.get('duration', '')
            
            logger.info(f'📞 DTMF received: {digit} (duration: {duration}ms) for {stream_id}')
            
            # Handle DTMF logic here
            # For now, just acknowledge
            
        except Exception as e:
            logger.error(f'❌ Error handling DTMF: {e}')
    async def cleanup_connections(self, stream_id: str):
        """Enhanced cleanup of both Exotel and OpenAI connections"""
        try:
            await self._clear_outbound(stream_id)
            self.outbound_buffers.pop(stream_id, None)
            self.outbound_pcm24.pop(stream_id, None)
            self.outbound_ratecv_state.pop(stream_id, None)
            self.inbound_ratecv_state.pop(stream_id, None)
            self.outbound_seq.pop(stream_id, None)
            self.outbound_flush.pop(stream_id, None)
            self.bot_speaking.pop(stream_id, None)
            self.instant_greeting_sent.pop(stream_id, None)

            # Close OpenAI connection
            if stream_id in self.openai_connections:
                openai_ws = self.openai_connections[stream_id]["websocket"]
                if not openai_ws.closed:
                    await openai_ws.close()
                del self.openai_connections[stream_id]
                logger.info(f"🧹 ENHANCED OPENAI CONNECTION REMOVED: {stream_id}")
            
            # Remove Exotel connection
            if stream_id in self.exotel_connections:
                del self.exotel_connections[stream_id]
                logger.info(f"🧹 ENHANCED EXOTEL CONNECTION REMOVED: {stream_id}")
            
            # Clean up enhanced audio buffers and settings
            if stream_id in self.audio_buffers:
                del self.audio_buffers[stream_id]
                logger.info(f"🧹 ENHANCED AUDIO BUFFER CLEARED: {stream_id}")
            
            if stream_id in self.connection_sample_rates:
                del self.connection_sample_rates[stream_id]
            
            if stream_id in self.connection_chunk_sizes:
                del self.connection_chunk_sizes[stream_id]
                
        except Exception as e:
            logger.error(f"❌ Error during enhanced cleanup: {e}")




async def main():
    """Enhanced main function to start the OpenAI Realtime Sales Bot"""
    try:
        # Initialize the enhanced sales bot
        sales_bot = OpenAIRealtimeSalesBot()
        
        # Start the enhanced WebSocket server
        await sales_bot.start_server()
        
    except Exception as e:
        logger.error(f'❌ Enhanced Server Error: {e}')
        raise


if __name__ == "__main__":
    asyncio.run(main()) 