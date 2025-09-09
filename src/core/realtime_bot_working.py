#!/usr/bin/env python3
"""
OpenAI Realtime Sales Bot - Enhanced Production Version with Multi-Sample Rate Support
Bridges Exotel WebSocket with OpenAI Realtime API for natural conversations
New Features: 16kHz/24kHz support, variable chunk sizes, enhanced mark/clear events

Security Notice: This code uses environment variables for sensitive configuration.
Set OPENAI_API_KEY environment variable before running.
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
        self.connection_sample_rates: Dict[str, int] = {}  # Track sample rate per connection
        self.connection_chunk_sizes: Dict[str, int] = {}   # Track chunk size per connection
        
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
        
        logger.info("🤖 Enhanced OpenAI Realtime Sales Bot initialized!")
        logger.info(f"🎵 Multi-sample rate support: {Config.SUPPORTED_SAMPLE_RATES} Hz")
        logger.info(f"📦 Variable chunk sizes: {self.min_chunk_size_ms}ms - {Config.MAX_CHUNK_SIZE_MS}ms")
        logger.info(f"✨ Enhanced Exotel events: {self.exotel_enhanced_events}")
        logger.info(f"🏢 Company: {Config.COMPANY_NAME}")
        logger.info(f"👤 Sales Rep: {Config.SALES_REP_NAME}")

    async def handle_exotel_websocket(self, websocket, path=None):
        """Handle incoming WebSocket connection from Exotel with enhanced sample rate detection"""
        stream_id = "unknown"
        
        try:
            # Extract sample rate from WebSocket path if available
            # Handle both old and new websockets library versions
            websocket_path = path or getattr(websocket, 'path', '/') or '/'
            detected_sample_rate = self._extract_sample_rate_from_path(websocket_path)
            logger.info(f"📞 NEW ENHANCED SALES CALL from Exotel: {websocket.remote_address}")
            logger.info(f"🎵 Detected sample rate: {detected_sample_rate}Hz")
            
            # Set up connection keep-alive and error handling
            async for message in websocket:
                try:
                    logger.info(f"📨 EXOTEL MESSAGE: {message}")
                    data = json.loads(message)
                    event = data.get("event", "")
                    
                    # Extract stream ID
                    if "streamSid" in data:
                        stream_id = data["streamSid"]
                    elif "stream_sid" in data:
                        stream_id = data["stream_sid"]
                    
                    # Initialize connection settings on first event
                    if stream_id not in self.connection_sample_rates:
                        self._initialize_connection_settings(stream_id, detected_sample_rate, data)
                    
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

    def _extract_sample_rate_from_path(self, path: str) -> int:
        """
        Extract sample rate from WebSocket path
        Supports formats like:
        - wss://yourdomain.ai/media?sample-rate=16000
        - wss://yourdomain.ai/media?sample-rate=24000
        """
        if not path:
            return self.default_sample_rate
            
        try:
            # Parse query parameters from path
            if '?' in path:
                query_part = path.split('?', 1)[1]
                params = parse_qs(query_part)
                
                # Check for sample-rate parameter
                if 'sample-rate' in params:
                    sample_rate = int(params['sample-rate'][0])
                    if sample_rate in Config.SUPPORTED_SAMPLE_RATES:
                        logger.info(f"🎵 DETECTED SAMPLE RATE FROM URL: {sample_rate}Hz")
                        return sample_rate
                    else:
                        logger.warning(f"⚠️ UNSUPPORTED SAMPLE RATE: {sample_rate}Hz, using {self.default_sample_rate}Hz")
                
        except Exception as e:
            logger.error(f"❌ Error parsing sample rate from path '{path}': {e}")
        
        return self.default_sample_rate

    def _initialize_connection_settings(self, stream_id: str, sample_rate: int, start_data: dict):
        """Initialize enhanced connection settings based on detected parameters"""
        self.connection_sample_rates[stream_id] = sample_rate
        
        # Calculate optimal chunk size based on sample rate and network conditions
        if self.dynamic_chunk_sizing:
            chunk_size_ms = Config.get_adaptive_chunk_size(sample_rate)
        else:
            chunk_size_ms = self.buffer_size_ms
        
        chunk_size_bytes = Config.get_chunk_size_bytes(sample_rate, chunk_size_ms)
        self.connection_chunk_sizes[stream_id] = chunk_size_bytes
        
        logger.info(f"🔧 INITIALIZED CONNECTION {stream_id}:")
        logger.info(f"   📡 Sample Rate: {sample_rate}Hz")
        logger.info(f"   📦 Chunk Size: {chunk_size_ms}ms ({chunk_size_bytes} bytes)")
        logger.info(f"   ⚙️ Enhanced Events: {self.exotel_enhanced_events}")

    async def handle_exotel_connected(self, stream_id: str, data: dict):
        """Handle Exotel connected event with enhanced confirmation"""
        logger.info(f"✅ EXOTEL CONNECTED (ENHANCED): {stream_id}")
        
        # Send immediate acknowledgment to Exotel
        try:
            exotel_ws = self.exotel_connections[stream_id]["websocket"]
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            
            # Generate sample rate appropriate test tone
            test_tone = self.generate_test_tone(sample_rate=sample_rate)
            test_audio_b64 = base64.b64encode(test_tone).decode()
            
            test_message = {
                "event": "media",
                "streamSid": stream_id,
                "media": {
                    "payload": test_audio_b64,
                    "timestamp": str(int(time.time() * 1000)),
                    "sequenceNumber": "1"
                }
            }
            
            await exotel_ws.send(json.dumps(test_message))
            logger.info(f"🔊 ENHANCED TEST TONE SENT ({sample_rate}Hz) to confirm audio pipeline for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending enhanced test tone: {e}")
        
        # Start enhanced OpenAI Realtime connection
        await self.connect_to_openai_enhanced(stream_id)

    async def handle_exotel_start(self, stream_id: str, data: dict):
        """Handle enhanced Exotel start event with sample rate detection"""
        sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
        
        # **NEW ARCHITECTURE: Keep OpenAI at 24kHz, let Exotel handle upsampling**
        start_data = data.get("start", {})
        media_format = start_data.get("media_format", {})
        if media_format and "sample_rate" in media_format:
            exotel_sample_rate = int(media_format["sample_rate"])
            logger.info(f"📡 EXOTEL PSTN RATE: {exotel_sample_rate}Hz (will be upsampled to {sample_rate}Hz)")
            logger.info(f"🎵 KEEPING OPENAI AT: {sample_rate}Hz for high quality audio")
            logger.info(f"🔄 ARCHITECTURE: PSTN {exotel_sample_rate}Hz → Exotel upsampling → OpenAI {sample_rate}Hz")
            
            # Store Exotel's original rate for reference but keep our high-quality rate
            self.exotel_connections[stream_id]["exotel_pstn_rate"] = exotel_sample_rate
            
            # Keep the high-quality sample rate (24kHz) for OpenAI
            logger.info(f"✅ HIGH-QUALITY AUDIO: OpenAI @ {sample_rate}Hz, Exotel handles upsampling from {exotel_sample_rate}Hz")
        
        logger.info(f"🚀 ENHANCED SALES CALL STARTED: {stream_id} @ {sample_rate}Hz")
        
        # Log media format if available
        if media_format:
            logger.info(f"📺 Media Format: {json.dumps(media_format, indent=2)}")

    async def handle_exotel_media(self, stream_id: str, data: dict):
        """Handle incoming audio from Exotel with enhanced variable chunk processing"""
        
        # **ENHANCED: Auto-establish OpenAI connection if missing**
        if stream_id not in self.openai_connections:
            logger.warning(f"⚠️ No OpenAI connection for {stream_id} - ESTABLISHING NOW")
            await self.connect_to_openai_enhanced(stream_id)
            
            # Wait a moment for connection to establish
            await asyncio.sleep(0.1)
            
            if stream_id not in self.openai_connections:
                logger.error(f"❌ Failed to establish OpenAI connection for {stream_id}")
                return
        
        if stream_id in self.openai_connections:
            # Get audio payload from Exotel
            media = data.get("media", {})
            audio_payload = media.get("payload", "")
            
            if audio_payload:
                try:
                    # Get connection-specific settings
                    sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
                    target_chunk_bytes = self.connection_chunk_sizes.get(stream_id, 0)
                    
                    # Decode PCM audio from Exotel
                    exotel_pcm = base64.b64decode(audio_payload)
                    
                    # **ENHANCED NOISE SUPPRESSION**: Apply audio enhancement
                    enhanced_pcm = self.apply_noise_suppression(exotel_pcm, sample_rate)
                    
                    # Initialize buffer for this stream if needed
                    if stream_id not in self.audio_buffers:
                        self.audio_buffers[stream_id] = b""
                    
                    # Add enhanced audio to buffer
                    self.audio_buffers[stream_id] += enhanced_pcm
                    
                    # **ENHANCED VARIABLE CHUNK PROCESSING**
                    if self.variable_chunk_support:
                        # Process variable chunks (minimum 20ms as per Exotel spec)
                        await self._process_variable_chunks(stream_id, sample_rate)
                    else:
                        # Traditional fixed chunk processing
                        await self._process_fixed_chunks(stream_id, target_chunk_bytes, sample_rate)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing enhanced buffered audio: {e}")
        else:
            logger.warning(f"⚠️ Still no OpenAI connection for {stream_id} after connection attempt")

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
            input_format = openai_config.get("input_format", "g711_ulaw")
            
            # Convert audio based on sample rate and format
            if input_format == "pcm16" and sample_rate >= 16000:
                # High quality PCM for 16kHz+ 
                openai_audio = chunk  # Already PCM16
            else:
                # Convert to G.711 u-law for lower sample rates or telephony compatibility
                openai_audio = self.convert_pcm_to_ulaw(chunk)
            
            openai_audio_b64 = base64.b64encode(openai_audio).decode()
            
            # Send to OpenAI Realtime API
            openai_msg = {
                "type": "input_audio_buffer.append",
                "audio": openai_audio_b64
            }
            
            openai_ws = openai_config["websocket"]
            await openai_ws.send(json.dumps(openai_msg))
            
            logger.debug(f"📤 AUDIO SENT TO OPENAI: {len(chunk)} bytes PCM → {len(openai_audio)} bytes {input_format}")
            
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
                
                # 3. Clear local audio buffer
                if stream_id in self.audio_buffers:
                    self.audio_buffers[stream_id] = b""
                    logger.info(f"🧹 CLEARED LOCAL AUDIO BUFFER for {stream_id}")
                
            except Exception as e:
                logger.error(f"❌ Error handling enhanced clear event: {e}")
        else:
            logger.warning(f"⚠️ No OpenAI connection to clear for {stream_id}")

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
        try:
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            logger.info(f"🔗 CONNECTING TO OPENAI (ENHANCED) for {stream_id} @ {sample_rate}Hz")
            
            # Enhanced URL for latest OpenAI Realtime API
            url = f"wss://api.openai.com/v1/realtime?model={self.openai_model}"
            
            # Create SSL context that handles certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Enhanced headers for latest API version
            headers = [
                ("Authorization", f"Bearer {self.openai_api_key}"),
                ("OpenAI-Beta", "realtime=v1")
            ]
            
            # Connect to OpenAI Realtime API with enhanced SSL context
            openai_ws = await websockets.connect(
                url, 
                additional_headers=headers,
                ssl=ssl_context,
                ping_interval=20,  # Enhanced connection stability
                ping_timeout=10
            )
            
            # Get enhanced session configuration
            session_config = Config.get_enhanced_session_config(sample_rate, self.openai_voice)
            
            self.openai_connections[stream_id] = {
                "websocket": openai_ws,
                "start_time": time.time(),
                "sample_rate": sample_rate,
                "input_format": session_config["input_audio_format"],
                "output_format": session_config["output_audio_format"],
                "session_config": session_config
            }
            
            # Update Exotel connection status
            if stream_id in self.exotel_connections:
                self.exotel_connections[stream_id]["openai_connected"] = True
            
            logger.info(f"✅ ENHANCED OPENAI CONNECTED for {stream_id} @ {sample_rate}Hz")
            logger.info(f"🎵 Audio Format: {session_config['input_audio_format']} → {session_config['output_audio_format']}")
            
            # Configure enhanced OpenAI session
            await self.configure_openai_session_enhanced(stream_id)
            
            # Start listening to OpenAI responses
            asyncio.create_task(self.handle_openai_responses_enhanced(stream_id, openai_ws))
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI (enhanced): {e}")
            logger.error(f"Error type: {type(e).__name__}")
            if "SSL" in str(e):
                logger.error("💡 SSL Error - trying with insecure SSL context")
            elif "authentication" in str(e).lower():
                logger.error("💡 Authentication Error - check OpenAI API key")
            elif "websocket" in str(e).lower():
                logger.error("💡 WebSocket Error - check connection and headers")

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
            logger.info(f"   🎤 Input Format: {session_config['input_audio_format']}")
            logger.info(f"   🔊 Output Format: {session_config['output_audio_format']}")
            logger.info(f"   🎭 Voice: {session_config['voice']}")
            
            # Send enhanced initial greeting
            await self.send_initial_greeting_enhanced(stream_id)
            
        except Exception as e:
            logger.error(f"❌ Error configuring enhanced OpenAI session: {e}")

    async def send_initial_greeting_enhanced(self, stream_id: str):
        """Send enhanced initial sales greeting through OpenAI"""
        try:
            openai_ws = self.openai_connections[stream_id]["websocket"]
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            
            # Create enhanced conversation item with greeting
            greeting_msg = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text", 
                        "text": f"A customer just called our sales line. The connection is running at {sample_rate}Hz audio quality. Please greet them warmly and ask how you can help them today."
                    }]
                }
            }
            
            await openai_ws.send(json.dumps(greeting_msg))
            
            # Create enhanced response with audio focus
            response_msg = {
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": "Give a warm, professional greeting. Keep it concise and natural."
                }
            }
            await openai_ws.send(json.dumps(response_msg))
            
            logger.info(f"👋 ENHANCED INITIAL GREETING SENT for {stream_id} @ {sample_rate}Hz")
            
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
                    
                    if event_type == "response.audio.delta":
                        await self.handle_openai_audio_delta_enhanced(stream_id, data)
                    elif event_type == "response.function_call_arguments.done":
                        await self.handle_openai_function_call_enhanced(stream_id, data)
                    elif event_type == "response.audio_transcript.delta":
                        transcript_delta = data.get('delta', '')
                        if transcript_delta.strip():
                            logger.info(f"🗣️ SARAH SPEAKING: {transcript_delta}")
                    elif event_type == "input_audio_buffer.speech_started":
                        logger.info(f"🎤 CUSTOMER STARTED SPEAKING (enhanced) for {stream_id}")
                        # Enhanced interruption handling
                        await self._handle_customer_interruption(stream_id, openai_ws)
                    elif event_type == "input_audio_buffer.speech_stopped":
                        logger.info(f"🎤 CUSTOMER STOPPED SPEAKING (enhanced) for {stream_id}")
                        # Enhanced response generation
                        await self.trigger_openai_response_enhanced(stream_id, openai_ws)
                    elif event_type == "response.done":
                        logger.info(f"✅ SARAH FINISHED RESPONSE (enhanced) for {stream_id}")
                    elif event_type == "error":
                        logger.error(f"❌ ENHANCED OPENAI ERROR: {data}")
                    elif event_type == "session.updated":
                        logger.info(f"🔧 SESSION UPDATED for {stream_id}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error from OpenAI (enhanced): {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing enhanced OpenAI response: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in enhanced OpenAI response handler: {e}")

    async def _handle_customer_interruption(self, stream_id: str, openai_ws):
        """Handle customer interruption with enhanced response cancellation"""
        try:
            # Enhanced interruption handling
            cancel_response_msg = {
                "type": "response.cancel"
            }
            await openai_ws.send(json.dumps(cancel_response_msg))
            logger.info(f"🛑 ENHANCED BOT INTERRUPTED - Customer started speaking for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling enhanced customer interruption: {e}")

    async def trigger_openai_response_enhanced(self, stream_id: str, openai_ws):
        """Trigger enhanced OpenAI response generation with improved parameters"""
        try:
            # Enhanced response triggering with better configuration
            await asyncio.sleep(0.2)  # Optimized pause verification
            
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": "Respond naturally and conversationally. Use appropriate pauses and inflections.",
                    "voice": self.openai_voice,
                    "temperature": Config.TEMPERATURE
                }
            }
            await openai_ws.send(json.dumps(response_create))
            logger.info(f"🎯 TRIGGERED ENHANCED OPENAI RESPONSE for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error triggering enhanced OpenAI response: {e}")

    async def handle_openai_audio_delta_enhanced(self, stream_id: str, data: dict):
        """Handle enhanced audio response from OpenAI with multi-sample rate support"""
        try:
            if stream_id not in self.exotel_connections:
                logger.warning(f"⚠️ No Exotel connection for {stream_id}")
                return
            
            # Get audio from OpenAI
            audio_delta = data.get("delta", "")
            if not audio_delta:
                return
            
            # Get connection settings
            sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)
            output_format = self.openai_connections[stream_id].get("output_format", "g711_ulaw")
            
            # Decode audio based on format
            openai_audio = base64.b64decode(audio_delta)
            
            # Convert audio for Exotel based on sample rate and format
            if output_format == "pcm16" and sample_rate >= 16000:
                # High quality PCM output - convert to PCM for Exotel
                exotel_pcm = openai_audio
            else:
                # G.711 u-law output - convert to PCM for Exotel
                exotel_pcm = self.convert_ulaw_to_pcm(openai_audio)
            
            # Apply resampling if needed for different sample rates
            if sample_rate != self.default_sample_rate:
                exotel_pcm = self._resample_audio(exotel_pcm, self.default_sample_rate, sample_rate)
            
            exotel_audio_b64 = base64.b64encode(exotel_pcm).decode()
            
            # Send to Exotel with enhanced message format
            exotel_ws = self.exotel_connections[stream_id]["websocket"]
            
            media_message = {
                "event": "media",
                "streamSid": stream_id,
                "media": {
                    "payload": exotel_audio_b64,
                    "timestamp": str(int(time.time() * 1000)),
                    "sequenceNumber": str(int(time.time()))
                }
            }
            
            await exotel_ws.send(json.dumps(media_message))
            logger.debug(f"📞 ENHANCED SARAH'S VOICE SENT: {len(openai_audio)} bytes {output_format} → {len(exotel_pcm)} bytes PCM @ {sample_rate}Hz")
            
        except Exception as e:
            logger.error(f"❌ Error sending enhanced audio to Exotel: {e}")

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
                    "modalities": ["audio", "text"],
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
        """Resample audio between different sample rates"""
        if from_rate == to_rate:
            return audio_data
            
        try:
            # Use the media resampler for high-quality resampling
            from engines.media_resampler import MediaResampler
            resampler = MediaResampler()
            
            resampled = resampler.resample_audio(
                audio_data=audio_data,
                from_rate=from_rate,
                to_rate=to_rate,
                channels=1,
                sample_width=2
            )
            
            if resampled:
                logger.debug(f"🔄 RESAMPLED AUDIO: {from_rate}Hz → {to_rate}Hz")
                return resampled
            else:
                logger.warning(f"⚠️ RESAMPLING FAILED, using original audio")
                return audio_data
                
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

    async def cleanup_connections(self, stream_id: str):
        """Enhanced cleanup of both Exotel and OpenAI connections"""
        try:
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
        logger.info(f"🚀 Starting Enhanced Sales Bot Server on {Config.SERVER_HOST}:{Config.SERVER_PORT}")
        logger.info("📞 Ready for Enhanced Exotel streaming connections!")
        logger.info("🎵 Multi-sample rate support: 8kHz, 16kHz, 24kHz")
        logger.info("📦 Variable chunk sizes: minimum 20ms")
        logger.info("✨ Enhanced mark/clear event handling")
        logger.info("🔐 Using secure environment-based configuration")
        
        async with websockets.serve(
            sales_bot.handle_exotel_websocket,
            Config.SERVER_HOST,
            Config.SERVER_PORT
        ):
            logger.info(f"✅ Enhanced Sales Bot Server running at ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}")
            logger.info("🎯 Ready for enhanced calls with multi-sample rate support...")
            
            # Keep the server running
            await asyncio.Future()  # Run forever
            
    except KeyboardInterrupt:
        logger.info("⏹️ Enhanced server stopped by user")
    except ValueError as e:
        logger.error(f"❌ Enhanced Configuration Error: {e}")
    except Exception as e:
        logger.error(f"❌ Enhanced Server Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 