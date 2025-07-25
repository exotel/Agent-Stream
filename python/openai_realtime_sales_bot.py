#!/usr/bin/env python3
"""
OpenAI Realtime Sales Bot - True Speech-to-Speech AI Sales Agent
Bridges Exotel WebSocket with OpenAI Realtime API for natural conversations

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
from typing import Dict, Any, Optional
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OpenAIRealtimeSalesBot:
    def __init__(self):
        # Validate configuration first
        Config.validate()
        
        self.exotel_connections: Dict[str, Dict[str, Any]] = {}
        self.openai_connections: Dict[str, Any] = {}
        
        # Audio buffering for better conversation flow
        self.audio_buffers: Dict[str, bytes] = {}  # Buffer audio for 200ms chunks
        self.buffer_size_ms = Config.BUFFER_SIZE_MS
        self.sample_rate = Config.SAMPLE_RATE
        self.bytes_per_chunk = int((self.sample_rate * 2 * self.buffer_size_ms) / 1000)  # 16-bit = 2 bytes per sample
        
        # OpenAI Configuration - SECURE: Load from environment variables
        self.openai_api_key = Config.OPENAI_API_KEY
        self.openai_realtime_url = f"wss://api.openai.com/v1/realtime?model={Config.OPENAI_MODEL}"
        
        # Sales Bot Configuration
        self.sales_instructions = Config.get_sales_instructions()

        logger.info("🤖 OpenAI Realtime Sales Bot initialized!")
        logger.info(f"🔊 Audio buffering: {self.buffer_size_ms}ms chunks ({self.bytes_per_chunk} bytes)")
        logger.info(f"🏢 Company: {Config.COMPANY_NAME}")
        logger.info(f"👤 Sales Rep: {Config.SALES_REP_NAME}")
        logger.info(f"📦 Products: {', '.join(Config.PRODUCTS)}")

    async def handle_exotel_websocket(self, websocket):
        """Handle incoming WebSocket connection from Exotel"""
        stream_id = "unknown"
        
        try:
            logger.info(f"📞 NEW SALES CALL from Exotel: {websocket.remote_address}")
            
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
                    
                    logger.info(f"🆔 STREAM ID: {stream_id}")
                    logger.info(f"🎯 EVENT: '{event}' for {stream_id}")
                    
                    # Store Exotel connection
                    if stream_id not in self.exotel_connections:
                        self.exotel_connections[stream_id] = {
                            "websocket": websocket,
                            "start_time": time.time(),
                            "openai_connected": False
                        }
                        logger.info(f"📞 NEW EXOTEL CONNECTION: {stream_id}")
                    
                    # Handle events
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
            logger.info(f"🧹 CLEANING UP CONNECTION: {stream_id}")
            await self.cleanup_connections(stream_id)

    async def handle_exotel_connected(self, stream_id: str, data: dict):
        """Handle Exotel connected event"""
        logger.info(f"✅ EXOTEL CONNECTED: {stream_id}")
        
        # Send immediate acknowledgment to Exotel
        try:
            exotel_ws = self.exotel_connections[stream_id]["websocket"]
            
            # Send a quick test beep to confirm audio pipeline is working
            test_tone = self.generate_test_tone()
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
            logger.info(f"🔊 TEST TONE SENT to confirm audio pipeline for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending test tone: {e}")
        
        # Start OpenAI Realtime connection
        await self.connect_to_openai(stream_id)

    async def handle_exotel_start(self, stream_id: str, data: dict):
        """Handle Exotel start event"""
        logger.info(f"🚀 SALES CALL STARTED: {stream_id}")

    async def handle_exotel_media(self, stream_id: str, data: dict):
        """Handle incoming audio from Exotel customer - buffer and forward to OpenAI"""
        
        # **FIX: Auto-establish OpenAI connection if missing**
        if stream_id not in self.openai_connections:
            logger.warning(f"⚠️ No OpenAI connection for {stream_id} - ESTABLISHING NOW")
            await self.connect_to_openai(stream_id)
            
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
                    # Decode PCM audio from Exotel
                    exotel_pcm = base64.b64decode(audio_payload)
                    
                    # **NOISE SUPPRESSION**: Apply audio enhancement
                    enhanced_pcm = self.apply_noise_suppression(exotel_pcm)
                    
                    # Initialize buffer for this stream if needed
                    if stream_id not in self.audio_buffers:
                        self.audio_buffers[stream_id] = b""
                    
                    # Add enhanced audio to buffer
                    self.audio_buffers[stream_id] += enhanced_pcm
                    
                    # Check if we have enough data for a 200ms chunk
                    if len(self.audio_buffers[stream_id]) >= self.bytes_per_chunk:
                        # Extract 200ms chunk
                        chunk = self.audio_buffers[stream_id][:self.bytes_per_chunk]
                        self.audio_buffers[stream_id] = self.audio_buffers[stream_id][self.bytes_per_chunk:]
                        
                        # Convert to G.711 u-law for OpenAI
                        openai_audio = self.convert_pcm_to_ulaw(chunk)
                        openai_audio_b64 = base64.b64encode(openai_audio).decode()
                        
                        # Send buffered chunk to OpenAI Realtime API
                        openai_msg = {
                            "type": "input_audio_buffer.append",
                            "audio": openai_audio_b64
                        }
                        
                        openai_ws = self.openai_connections[stream_id]["websocket"]
                        await openai_ws.send(json.dumps(openai_msg))
                        logger.info(f"📤 SENT 200ms AUDIO CHUNK TO OPENAI: {len(chunk)} bytes PCM → {len(openai_audio)} bytes G.711 for {stream_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing buffered audio: {e}")
        else:
            logger.warning(f"⚠️ Still no OpenAI connection for {stream_id} after connection attempt")

    async def handle_exotel_stop(self, stream_id: str, data: dict):
        """Handle Exotel stop event"""
        logger.info(f"🛑 SALES CALL ENDED: {stream_id}")

    async def handle_exotel_mark(self, stream_id: str, data: dict):
        """Handle Exotel mark event - audio playback position marker"""
        mark_name = data.get("mark", {}).get("name", "unknown")
        logger.info(f"📍 EXOTEL MARK: {mark_name} for {stream_id}")
        
        # Mark events can be used to synchronize audio playback
        # For example, when a specific audio chunk has been played
        if mark_name == "greeting_complete":
            logger.info(f"✅ GREETING COMPLETED for {stream_id}")
        elif mark_name == "response_start":
            logger.info(f"🎯 RESPONSE PLAYBACK STARTED for {stream_id}")

    async def handle_exotel_clear(self, stream_id: str, data: dict):
        """Handle Exotel clear event - clear audio buffer and STOP bot speaking"""
        logger.info(f"🧹 EXOTEL CLEAR - INTERRUPTING BOT SPEECH: {stream_id}")
        
        if stream_id in self.openai_connections:
            try:
                openai_ws = self.openai_connections[stream_id]["websocket"]
                
                # 1. Clear OpenAI's input audio buffer
                clear_input_msg = {
                    "type": "input_audio_buffer.clear"
                }
                await openai_ws.send(json.dumps(clear_input_msg))
                logger.info(f"🧹 CLEARED OPENAI INPUT BUFFER for {stream_id}")
                
                # 2. CANCEL any ongoing response (this stops the bot mid-speech)
                cancel_response_msg = {
                    "type": "response.cancel"
                }
                await openai_ws.send(json.dumps(cancel_response_msg))
                logger.info(f"🛑 CANCELLED ONGOING RESPONSE (bot interrupted) for {stream_id}")
                
                # 3. Clear local audio buffer too
                if stream_id in self.audio_buffers:
                    self.audio_buffers[stream_id] = b""
                    logger.info(f"🧹 CLEARED LOCAL AUDIO BUFFER for {stream_id}")
                
            except Exception as e:
                logger.error(f"❌ Error handling clear event: {e}")
        else:
            logger.warning(f"⚠️ No OpenAI connection to clear for {stream_id}")

    async def connect_to_openai(self, stream_id: str):
        """Establish connection to OpenAI Realtime API"""
        try:
            logger.info(f"🔗 CONNECTING TO OPENAI for {stream_id}")
            
            # URL for OpenAI Realtime API
            url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            
            # Create SSL context that handles certificate verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create custom headers for websockets 15.0.1
            headers = [
                ("Authorization", f"Bearer {self.openai_api_key}"),
                ("OpenAI-Beta", "realtime=v1")
            ]
            
            # Connect to OpenAI Realtime API with SSL context
            openai_ws = await websockets.connect(
                url, 
                additional_headers=headers,
                ssl=ssl_context
            )
            
            self.openai_connections[stream_id] = {
                "websocket": openai_ws,
                "start_time": time.time()
            }
            
            # Update Exotel connection status
            if stream_id in self.exotel_connections:
                self.exotel_connections[stream_id]["openai_connected"] = True
            
            logger.info(f"✅ OPENAI CONNECTED for {stream_id}")
            
            # Configure OpenAI session for sales
            await self.configure_openai_session(stream_id)
            
            # Start listening to OpenAI responses
            asyncio.create_task(self.handle_openai_responses(stream_id, openai_ws))
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            # Try to provide helpful error context
            if "SSL" in str(e):
                logger.error("💡 SSL Error - trying with insecure SSL context")
            elif "authentication" in str(e).lower():
                logger.error("💡 Authentication Error - check OpenAI API key")
            elif "websocket" in str(e).lower():
                logger.error("💡 WebSocket Error - check connection and headers")

    async def configure_openai_session(self, stream_id: str):
        """Configure OpenAI Realtime session for sales conversations"""
        try:
            openai_ws = self.openai_connections[stream_id]["websocket"]
            
            # Session configuration - USE 8kHz to match Exotel!
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self.sales_instructions,
                    "voice": "alloy",
                    "input_audio_format": "g711_ulaw",  # 8kHz format to match Exotel
                    "output_audio_format": "g711_ulaw", # 8kHz format to match Exotel
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": Config.VAD_THRESHOLD,  # Configurable speech detection
                        "prefix_padding_ms": Config.PREFIX_PADDING_MS,  # Configurable padding
                        "silence_duration_ms": Config.SILENCE_DURATION_MS  # Configurable silence duration
                    },
                    "temperature": 0.7,
                    "tools": [
                        {
                            "type": "function",
                            "name": "schedule_demo",
                            "description": "Schedule a product demo for the customer",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "customer_name": {"type": "string"},
                                    "company": {"type": "string"},
                                    "product_interest": {"type": "string"},
                                    "preferred_time": {"type": "string"}
                                },
                                "required": ["customer_name", "product_interest"]
                            }
                        },
                        {
                            "type": "function",
                            "name": "send_pricing_info",
                            "description": "Send pricing information to customer",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "product": {"type": "string"},
                                    "company_size": {"type": "string"}
                                },
                                "required": ["product"]
                            }
                        }
                    ]
                }
            }
            
            await openai_ws.send(json.dumps(session_config))
            logger.info(f"🔧 OPENAI SESSION CONFIGURED (8kHz G.711) for {stream_id}")
            
            # Send initial greeting
            await self.send_initial_greeting(stream_id)
            
        except Exception as e:
            logger.error(f"❌ Error configuring OpenAI session: {e}")

    async def send_initial_greeting(self, stream_id: str):
        """Send initial sales greeting through OpenAI"""
        try:
            openai_ws = self.openai_connections[stream_id]["websocket"]
            
            # Create conversation item with greeting
            greeting_msg = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text", 
                        "text": "A customer just called our sales line. Please greet them warmly and ask how you can help them today."
                    }]
                }
            }
            
            await openai_ws.send(json.dumps(greeting_msg))
            
            # Create response
            response_msg = {"type": "response.create"}
            await openai_ws.send(json.dumps(response_msg))
            
            logger.info(f"👋 INITIAL GREETING SENT for {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending initial greeting: {e}")

    async def handle_openai_responses(self, stream_id: str, openai_ws):
        """Handle responses from OpenAI Realtime API"""
        try:
            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type", "")
                    
                    logger.info(f"🤖 OPENAI EVENT: {event_type} for {stream_id}")
                    
                    if event_type == "response.audio.delta":
                        await self.handle_openai_audio_delta(stream_id, data)
                    elif event_type == "response.function_call_arguments.done":
                        await self.handle_openai_function_call(stream_id, data)
                    elif event_type == "response.audio_transcript.delta":
                        logger.info(f"🗣️ SARAH SPEAKING: {data.get('delta', '')}")
                    elif event_type == "input_audio_buffer.speech_started":
                        logger.info(f"🎤 CUSTOMER STARTED SPEAKING for {stream_id}")
                        # **INTERRUPTION HANDLING**: Cancel ongoing response when customer starts speaking
                        try:
                            cancel_response_msg = {
                                "type": "response.cancel"
                            }
                            await openai_ws.send(json.dumps(cancel_response_msg))
                            logger.info(f"🛑 BOT INTERRUPTED - Customer started speaking for {stream_id}")
                        except Exception as e:
                            logger.error(f"❌ Error cancelling response on interruption: {e}")
                    elif event_type == "input_audio_buffer.speech_stopped":
                        logger.info(f"🎤 CUSTOMER STOPPED SPEAKING for {stream_id}")
                        # Customer finished speaking - trigger response generation
                        await self.trigger_openai_response(stream_id, openai_ws)
                    elif event_type == "response.done":
                        logger.info(f"✅ SARAH FINISHED RESPONSE for {stream_id}")
                    elif event_type == "error":
                        logger.error(f"❌ OPENAI ERROR: {data}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error from OpenAI: {e}")
                except Exception as e:
                    logger.error(f"❌ Error processing OpenAI response: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in OpenAI response handler: {e}")

    async def trigger_openai_response(self, stream_id: str, openai_ws):
        """Trigger OpenAI to generate a response after customer stops speaking"""
        try:
            # Add a small delay to ensure customer has truly finished
            await asyncio.sleep(0.3)  # 300ms additional pause verification
            
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["audio"],
                    "instructions": "Keep your response brief and conversational. Speak naturally with pauses."
                }
            }
            await openai_ws.send(json.dumps(response_create))
            logger.info(f"🎯 TRIGGERED OPENAI RESPONSE for {stream_id} (after silence verification)")
            
        except Exception as e:
            logger.error(f"❌ Error triggering OpenAI response: {e}")

    async def handle_openai_audio_delta(self, stream_id: str, data: dict):
        """Handle audio response from OpenAI - send to Exotel"""
        try:
            if stream_id not in self.exotel_connections:
                logger.warning(f"⚠️ No Exotel connection for {stream_id}")
                return
            
            # Get audio from OpenAI (G.711 u-law 8kHz)
            audio_delta = data.get("delta", "")
            if not audio_delta:
                return
            
            # Convert from G.711 u-law to PCM for Exotel
            openai_ulaw = base64.b64decode(audio_delta)
            exotel_pcm = self.convert_ulaw_to_pcm(openai_ulaw)
            exotel_audio_b64 = base64.b64encode(exotel_pcm).decode()
            
            # Send to Exotel
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
            logger.info(f"📞 SARAH'S VOICE SENT TO CUSTOMER: {len(openai_ulaw)} bytes G.711 → {len(exotel_pcm)} bytes PCM")
            
        except Exception as e:
            logger.error(f"❌ Error sending audio to Exotel: {e}")

    async def handle_openai_function_call(self, stream_id: str, data: dict):
        """Handle function calls from OpenAI (e.g., schedule demo)"""
        try:
            function_name = data.get("name", "")
            arguments = json.loads(data.get("arguments", "{}"))
            
            logger.info(f"🔧 FUNCTION CALL: {function_name} with {arguments}")
            
            # Execute function and send result back to OpenAI
            if function_name == "schedule_demo":
                result = await self.schedule_demo(arguments)
            elif function_name == "send_pricing_info":
                result = await self.send_pricing_info(arguments)
            else:
                result = {"status": "unknown_function"}
            
            # Send function result back to OpenAI
            openai_ws = self.openai_connections[stream_id]["websocket"]
            
            function_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": data.get("call_id"),
                    "output": json.dumps(result)
                }
            }
            
            await openai_ws.send(json.dumps(function_response))
            
            # Create new response
            await openai_ws.send(json.dumps({"type": "response.create"}))
            
        except Exception as e:
            logger.error(f"❌ Error handling function call: {e}")

    async def schedule_demo(self, args: dict) -> dict:
        """Schedule a demo for the customer"""
        logger.info(f"📅 SCHEDULING DEMO: {args}")
        return {
            "status": "success",
            "message": f"Demo scheduled for {args.get('customer_name', 'customer')} interested in {args.get('product_interest', 'our solutions')}"
        }

    async def send_pricing_info(self, args: dict) -> dict:
        """Send pricing information"""
        logger.info(f"💰 SENDING PRICING INFO: {args}")
        return {
            "status": "success", 
            "message": f"Pricing information for {args.get('product', 'our solution')} will be sent to your email"
        }

    def convert_pcm_to_ulaw(self, pcm_data: bytes) -> bytes:
        """Convert 16-bit PCM to G.711 u-law (same sample rate 8kHz)"""
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
        """Convert G.711 u-law to 16-bit PCM (same sample rate 8kHz)"""
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

    def apply_noise_suppression(self, audio_data: bytes) -> bytes:
        """Apply basic noise suppression and audio enhancement for telephony"""
        try:
            # Convert bytes to numpy array for processing
            import numpy as np
            
            # Convert to 16-bit signed integers
            audio_samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Basic noise gate - suppress very quiet audio (likely noise)
            noise_threshold = Config.NOISE_THRESHOLD  # Configurable noise threshold
            audio_samples = np.where(np.abs(audio_samples) < noise_threshold, 0, audio_samples)
            
            # Simple high-pass filter to remove low-frequency noise (< 300Hz)
            # This helps with telephony noise and rumble
            if len(audio_samples) > 10:
                # Very basic high-pass: subtract moving average
                window_size = min(5, len(audio_samples) // 2)
                moving_avg = np.convolve(audio_samples.astype(np.float32), 
                                       np.ones(window_size)/window_size, mode='same')
                audio_samples = audio_samples - moving_avg.astype(np.int16) * 0.1
            
            # Gentle compression to normalize levels
            max_val = np.max(np.abs(audio_samples))
            if max_val > 0:
                # Compress dynamic range slightly
                compression_ratio = 0.8
                normalized = audio_samples.astype(np.float32) / max_val
                compressed = np.sign(normalized) * (np.abs(normalized) ** compression_ratio)
                audio_samples = (compressed * max_val * 0.9).astype(np.int16)
            
            # Convert back to bytes
            return audio_samples.tobytes()
            
        except ImportError:
            logger.warning("📢 NumPy not available - skipping noise suppression")
            return audio_data
        except Exception as e:
            logger.error(f"❌ Error in noise suppression: {e}")
            return audio_data

    async def cleanup_connections(self, stream_id: str):
        """Clean up both Exotel and OpenAI connections"""
        try:
            # Close OpenAI connection
            if stream_id in self.openai_connections:
                openai_ws = self.openai_connections[stream_id]["websocket"]
                if not openai_ws.closed:
                    await openai_ws.close()
                del self.openai_connections[stream_id]
                logger.info(f"🧹 OPENAI CONNECTION REMOVED: {stream_id}")
            
            # Remove Exotel connection
            if stream_id in self.exotel_connections:
                del self.exotel_connections[stream_id]
                logger.info(f"🧹 EXOTEL CONNECTION REMOVED: {stream_id}")
            
            # Clean up audio buffer
            if stream_id in self.audio_buffers:
                del self.audio_buffers[stream_id]
                logger.info(f"🧹 AUDIO BUFFER CLEARED: {stream_id}")
                
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

    def generate_test_tone(self, duration_ms: int = 200, frequency: int = 800) -> bytes:
        """Generate a brief test tone to confirm audio pipeline"""
        import math
        
        sample_rate = 8000  # 8kHz for Exotel
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

async def main():
    """Main function to start the OpenAI Realtime Sales Bot"""
    try:
        # Initialize the sales bot
        sales_bot = OpenAIRealtimeSalesBot()
        
        # Start the WebSocket server
        logger.info(f"🚀 Starting Sales Bot Server on {Config.SERVER_HOST}:{Config.SERVER_PORT}")
        logger.info("📞 Ready for Exotel streaming connections!")
        logger.info("🔐 Using secure environment-based configuration")
        
        async with websockets.serve(
            sales_bot.handle_exotel_websocket,
            Config.SERVER_HOST,
            Config.SERVER_PORT
        ):
            logger.info(f"✅ Sales Bot Server running at ws://{Config.SERVER_HOST}:{Config.SERVER_PORT}")
            logger.info("🎯 Waiting for calls...")
            
            # Keep the server running
            await asyncio.Future()  # Run forever
            
    except KeyboardInterrupt:
        logger.info("⏹️ Server stopped by user")
    except ValueError as e:
        logger.error(f"❌ Configuration Error: {e}")
    except Exception as e:
        logger.error(f"❌ Server Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 