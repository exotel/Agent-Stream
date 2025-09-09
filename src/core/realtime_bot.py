#!/usr/bin/env python3
"""
Exotel AgentStream - OpenAI Realtime Bot Integration
===================================================

SAMPLE CODE FOR TESTING AND DEVELOPMENT

Copyright (c) 2025 Exotel Techcom Pvt. Ltd.
Licensed under the MIT License.

A production-ready WebSocket bot that integrates with OpenAI's Realtime API
for voice conversations. Optimized for Exotel AgentStream voice streaming
platform with support for multiple sample rates and adaptive chunk sizing.

WSS Endpoint Configuration for Exotel Voicebot Applet:
- wss://your-domain.com/?sample-rate=8000   (Standard PSTN)
- wss://your-domain.com/?sample-rate=16000  (Enhanced quality)
- wss://your-domain.com/?sample-rate=24000  (HD quality - Beta)

Features:
- Multi-sample rate support (8kHz, 16kHz, 24kHz)
- Adaptive chunk sizing (20ms-200ms)
- High-quality audio processing
- Robust error handling and logging
- Production-ready configuration management
- Scalable architecture

Author: Agent Stream Team
Version: 2.0.0
License: MIT
"""

import asyncio
import websockets
import json
import base64
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

# Import configuration
from config.settings import Config

# Setup logging
logging.basicConfig(
 level=logging.INFO,
 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
 handlers=[
 logging.FileHandler('logs/realtime_bot.log'),
 logging.StreamHandler()
 ]
)
logger = logging.getLogger(__name__)

class OpenAIRealtimeBot:
 """
 Production-ready OpenAI Realtime Bot for voice conversations.

 This bot handles WebSocket connections from telephony providers (like Exotel),
 processes audio streams, and integrates with OpenAI's Realtime API for
 natural voice conversations.
               """

    def __init__(self):
        """Initialize the bot with production configuration."""
        # Core configuration
        self.openai_api_key = Config.OPENAI_API_KEY
        self.openai_model = Config.OPENAI_MODEL
        self.openai_voice = Config.OPENAI_VOICE
        self.server_host = Config.SERVER_HOST
        self.server_port = Config.SERVER_PORT
        self.default_sample_rate = Config.DEFAULT_SAMPLE_RATE

        # Audio processing configuration
        self.min_chunk_size_ms = Config.MIN_CHUNK_SIZE_MS
        self.max_chunk_size_ms = Config.MAX_CHUNK_SIZE_MS
        self.buffer_size_ms = Config.BUFFER_SIZE_MS

        # Feature flags
        self.enhanced_events = Config.ENHANCED_EVENTS_ENABLED
        self.dynamic_chunk_sizing = Config.DYNAMIC_CHUNK_SIZING
        self.audio_enhancement = Config.AUDIO_ENHANCEMENT_ENABLED

        # Connection tracking
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.openai_connections: Dict[str, Dict[str, Any]] = {}
        self.connection_sample_rates: Dict[str, int] = {}
        self.connection_chunk_sizes: Dict[str, int] = {}

 # Validate configuration
 self._validate_configuration()

 logger.info("OpenAI Realtime Bot initialized (Production v2.0)")
 logger.info(f"Sample rate support: {Config.SUPPORTED_SAMPLE_RATES} Hz")
 logger.info(f"Chunk sizes: {self.min_chunk_size_ms}ms - {self.max_chunk_size_ms}ms")
 logger.info(f"Enhanced features: {self.enhanced_events}")
 logger.info(f"Company: {Config.COMPANY_NAME}")
 logger.info(f"Assistant: {Config.ASSISTANT_NAME}")

 def _validate_configuration(self):
 """Validate critical configuration parameters."""
 if not self.openai_api_key:
 raise ValueError("OPENAI_API_KEY is required")

 if self.default_sample_rate not in Config.SUPPORTED_SAMPLE_RATES:
 raise ValueError(f"Invalid sample rate: {self.default_sample_rate}")

 logger.info("Configuration validated successfully")

 def _extract_sample_rate_from_path(self, path: str) -> int:
 """Extract sample rate from WebSocket path parameters."""
 try:
 parsed_url = urlparse(path)
 query_params = parse_qs(parsed_url.query)

 if 'sample-rate' in query_params:
 sample_rate = int(query_params['sample-rate'][0])
 if sample_rate in Config.SUPPORTED_SAMPLE_RATES:
 return sample_rate
 else:
 logger.warning(f"Unsupported sample rate {sample_rate}, using default {self.default_sample_rate}")

 except Exception as e:
 logger.warning(f"Failed to extract sample rate from path: {e}")

 return self.default_sample_rate

 def _initialize_connection_settings(self, stream_id: str, sample_rate: int, start_data: dict):
 """Initialize connection settings with adaptive configuration."""
 self.connection_sample_rates[stream_id] = sample_rate

 # Calculate optimal chunk size
 if self.dynamic_chunk_sizing:
 chunk_size_ms = Config.get_adaptive_chunk_size(sample_rate)
 else:
 chunk_size_ms = self.buffer_size_ms

 chunk_size_bytes = Config.get_chunk_size_bytes(sample_rate, chunk_size_ms)
 self.connection_chunk_sizes[stream_id] = chunk_size_bytes

 logger.info(f"CONNECTION INITIALIZED: {stream_id}")
 logger.info(f" Sample Rate: {sample_rate}Hz")
 logger.info(f" Chunk Size: {chunk_size_ms}ms ({chunk_size_bytes} bytes)")
 logger.info(f" Enhanced Events: {self.enhanced_events}")

 async def handle_websocket_connection(self, websocket, path=None):
 """
 Handle incoming WebSocket connection from telephony provider.

 This is the main entry point for all WebSocket connections.
 Supports both legacy and modern websockets library versions.
 """
 stream_id = "unknown"

 try:
 # Handle both old and new websockets library versions
 websocket_path = path or getattr(websocket, 'path', '/') or '/'
 detected_sample_rate = self._extract_sample_rate_from_path(websocket_path)

 logger.info(f"NEW CONNECTION: {websocket.remote_address}")
 logger.info(f"Detected sample rate: {detected_sample_rate}Hz")

 # Generate unique stream ID
 stream_id = str(uuid.uuid4())[:8]

 # Store connection info
 self.connections[stream_id] = {
 "websocket": websocket,
 "connected_at": time.time(),
 "openai_connected": False,
 "sample_rate": detected_sample_rate,
 "chunk_size_bytes": 0,
 "path": websocket_path
 }

 logger.info(f"CONNECTION REGISTERED: {stream_id} @ {detected_sample_rate}Hz")

 # Handle messages
 async for message in websocket:
 try:
 data = json.loads(message)
 event_type = data.get("event", "unknown")

 logger.info(f"EVENT: {event_type} from {stream_id}")

 # Route events to appropriate handlers
 if event_type == "connected":
 await self.handle_connected_event(stream_id, data)
 elif event_type == "start":
 await self.handle_start_event(stream_id, data)
 elif event_type == "media":
 await self.handle_media_event(stream_id, data)
 elif event_type == "mark":
 await self.handle_mark_event(stream_id, data)
 elif event_type == "clear":
 await self.handle_clear_event(stream_id, data)
 elif event_type == "stop":
 await self.handle_stop_event(stream_id, data)
 else:
 logger.warning(f"Unknown event type: {event_type}")

 except json.JSONDecodeError as e:
 logger.error(f"Invalid JSON received: {e}")
 except Exception as e:
 logger.error(f"Error processing message: {e}")

 except websockets.exceptions.ConnectionClosed:
 logger.info(f"Connection closed: {stream_id}")
 except Exception as e:
 logger.error(f"Connection error: {e}")
 finally:
 await self._cleanup_connection(stream_id)

 async def handle_connected_event(self, stream_id: str, data: dict):
 """Handle telephony provider connected event."""
 logger.info(f"CONNECTED: {stream_id}")

 # Send acknowledgment if needed
 try:
 websocket = self.connections[stream_id]["websocket"]
 sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)

 # Generate test tone for connection verification
 test_tone = self._generate_test_tone(sample_rate=sample_rate)
 test_audio_b64 = base64.b64encode(test_tone).decode()

 # Send test audio
 test_message = {
 "event": "media",
 "streamSid": stream_id,
 "media": {
 "payload": test_audio_b64
 }
 }

 await websocket.send(json.dumps(test_message))
 logger.info(f"Test tone sent to {stream_id}")

 except Exception as e:
 logger.error(f"Failed to send test tone: {e}")

 async def handle_start_event(self, stream_id: str, data: dict):
 """Handle call start event with sample rate detection."""
 sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)

 # **NEW ARCHITECTURE: Keep OpenAI at 24kHz, let telephony provider handle upsampling**
 start_data = data.get("start", {})
 media_format = start_data.get("media_format", {})

 if media_format and "sample_rate" in media_format:
 provider_sample_rate = int(media_format["sample_rate"])
 logger.info(f"PROVIDER RATE: {provider_sample_rate}Hz (will be upsampled to {sample_rate}Hz)")
 logger.info(f"KEEPING OPENAI AT: {sample_rate}Hz for high quality audio")
 logger.info(f"ARCHITECTURE: PSTN {provider_sample_rate}Hz → Provider upsampling → OpenAI {sample_rate}Hz")

 # Store provider's original rate for reference
 self.connections[stream_id]["provider_pstn_rate"] = provider_sample_rate

 logger.info(f"HIGH-QUALITY AUDIO: OpenAI @ {sample_rate}Hz, Provider handles upsampling from {provider_sample_rate}Hz")

 logger.info(f"CALL STARTED: {stream_id} @ {sample_rate}Hz")

 # Initialize connection settings
 self._initialize_connection_settings(stream_id, sample_rate, start_data)

 # Connect to OpenAI
 await self._connect_to_openai(stream_id)

 # Send initial greeting
 await self._send_initial_greeting(stream_id)

 async def handle_media_event(self, stream_id: str, data: dict):
 """Handle incoming audio media from telephony provider."""
 try:
 if stream_id not in self.openai_connections:
 logger.warning(f"No OpenAI connection for {stream_id}")
 return

 media = data.get("media", {})
 audio_payload = media.get("payload", "")

 if not audio_payload:
 return

 # Decode audio
 try:
 audio_data = base64.b64decode(audio_payload)
 except Exception as e:
 logger.error(f"Failed to decode audio: {e}")
 return

 # Send to OpenAI
 openai_ws = self.openai_connections[stream_id]["websocket"]

 # Format for OpenAI Realtime API
 openai_message = {
 "type": "input_audio_buffer.append",
 "audio": base64.b64encode(audio_data).decode()
 }

 await openai_ws.send(json.dumps(openai_message))

 except Exception as e:
 logger.error(f"Error handling media: {e}")

 async def handle_mark_event(self, stream_id: str, data: dict):
 """Handle mark event for audio synchronization."""
 if self.enhanced_events:
 logger.info(f"MARK: {stream_id} - {data.get('mark', {}).get('name', 'unnamed')}")

 async def handle_clear_event(self, stream_id: str, data: dict):
 """Handle clear event for audio buffer management."""
 if self.enhanced_events:
 logger.info(f"CLEAR: {stream_id}")

 # Clear OpenAI audio buffer if connected
 if stream_id in self.openai_connections:
 try:
 openai_ws = self.openai_connections[stream_id]["websocket"]
 clear_message = {"type": "input_audio_buffer.clear"}
 await openai_ws.send(json.dumps(clear_message))
 logger.info(f"OpenAI buffer cleared for {stream_id}")
 except Exception as e:
 logger.error(f"Failed to clear OpenAI buffer: {e}")

 async def handle_stop_event(self, stream_id: str, data: dict):
 """Handle call stop event."""
 logger.info(f"CALL STOPPED: {stream_id}")
 await self._cleanup_connection(stream_id)

 async def _connect_to_openai(self, stream_id: str):
 """Establish connection to OpenAI Realtime API."""
 try:
 sample_rate = self.connection_sample_rates.get(stream_id, self.default_sample_rate)

 # Get session configuration
 session_config = Config.get_session_config(sample_rate, self.openai_voice)

 # Connect to OpenAI
 openai_ws = await websockets.connect(
 "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17",
 extra_headers={
 "Authorization": f"Bearer {self.openai_api_key}",
 "OpenAI-Beta": "realtime=v1"
 }
 )

 # Store connection
 self.openai_connections[stream_id] = {
 "websocket": openai_ws,
 "session_config": session_config,
 "sample_rate": sample_rate,
 "connected_at": time.time()
 }

 # Configure session
 await openai_ws.send(json.dumps({
 "type": "session.update",
 "session": session_config
 }))

 # Start listening for OpenAI responses
 asyncio.create_task(self._handle_openai_messages(stream_id))

 logger.info(f"OpenAI connected: {stream_id} @ {sample_rate}Hz")

 except Exception as e:
 logger.error(f"Failed to connect to OpenAI: {e}")

 async def _handle_openai_messages(self, stream_id: str):
 """Handle messages from OpenAI Realtime API."""
 try:
 if stream_id not in self.openai_connections:
 return

 openai_ws = self.openai_connections[stream_id]["websocket"]

 async for message in openai_ws:
 try:
 data = json.loads(message)
 message_type = data.get("type", "unknown")

 if message_type == "response.audio.delta":
 # Handle audio response from OpenAI
 await self._handle_openai_audio_response(stream_id, data)
 elif message_type == "session.created":
 logger.info(f"OpenAI session created: {stream_id}")
 elif message_type == "error":
 logger.error(f"OpenAI error: {data}")

 except json.JSONDecodeError as e:
 logger.error(f"Invalid JSON from OpenAI: {e}")
 except Exception as e:
 logger.error(f"Error processing OpenAI message: {e}")

 except websockets.exceptions.ConnectionClosed:
 logger.info(f"OpenAI connection closed: {stream_id}")
 except Exception as e:
 logger.error(f"OpenAI connection error: {e}")

 async def _handle_openai_audio_response(self, stream_id: str, data: dict):
 """Handle audio response from OpenAI and send to telephony provider."""
 try:
 if stream_id not in self.connections:
 return

 audio_delta = data.get("delta", "")
 if not audio_delta:
 return

 # Send audio to telephony provider
 provider_ws = self.connections[stream_id]["websocket"]

 response_message = {
 "event": "media",
 "streamSid": stream_id,
 "media": {
 "payload": audio_delta
 }
 }

 await provider_ws.send(json.dumps(response_message))

 except Exception as e:
 logger.error(f"Error sending audio response: {e}")

 async def _send_initial_greeting(self, stream_id: str):
 """Send initial greeting through OpenAI."""
 try:
 if stream_id not in self.openai_connections:
 return

 openai_ws = self.openai_connections[stream_id]["websocket"]

 greeting_message = {
 "type": "response.create",
 "response": {
 "modalities": ["audio", "text"],
 "instructions": "Give a warm, professional greeting. Keep it concise and natural."
 }
 }

 await openai_ws.send(json.dumps(greeting_message))
 logger.info(f"👋 Initial greeting sent: {stream_id}")

 except Exception as e:
 logger.error(f"Failed to send greeting: {e}")

 def _generate_test_tone(self, sample_rate: int, duration_ms: int = 100) -> bytes:
 """Generate a test tone for connection verification."""
 import math

 samples = int(sample_rate * duration_ms / 1000)
 frequency = 440 # A4 note

 audio_data = bytearray()
 for i in range(samples):
 # Generate sine wave
 sample = int(16383 * math.sin(2 * math.pi * frequency * i / sample_rate))
 # Convert to 16-bit PCM
 audio_data.extend(sample.to_bytes(2, byteorder='little', signed=True))

 return bytes(audio_data)

 async def _cleanup_connection(self, stream_id: str):
 """Clean up connection resources."""
 try:
 # Close OpenAI connection
 if stream_id in self.openai_connections:
 try:
 openai_ws = self.openai_connections[stream_id]["websocket"]
 if hasattr(openai_ws, 'close'):
 await openai_ws.close()
 except Exception as e:
 logger.warning(f"Error closing OpenAI connection: {e}")
 finally:
 del self.openai_connections[stream_id]

 # Clean up connection data
 if stream_id in self.connections:
 del self.connections[stream_id]

 if stream_id in self.connection_sample_rates:
 del self.connection_sample_rates[stream_id]

 if stream_id in self.connection_chunk_sizes:
 del self.connection_chunk_sizes[stream_id]

 logger.info(f"Cleaned up connection: {stream_id}")

 except Exception as e:
 logger.error(f"Error during cleanup: {e}")

 async def start_server(self):
 """Start the WebSocket server."""
 logger.info(f"Starting OpenAI Realtime Bot Server on {self.server_host}:{self.server_port}")
 logger.info(f"Ready for telephony connections!")
 logger.info(f"Multi-sample rate support: {', '.join(map(str, Config.SUPPORTED_SAMPLE_RATES))}Hz")
 logger.info(f"Adaptive chunk sizing: {self.min_chunk_size_ms}ms - {self.max_chunk_size_ms}ms")
 logger.info(f"Enhanced features enabled: {self.enhanced_events}")
 logger.info(f"Using secure environment-based configuration")

 async with websockets.serve(
 self.handle_websocket_connection,
 self.server_host,
 self.server_port
 ):
 logger.info(f"Server running at ws://{self.server_host}:{self.server_port}")
 logger.info("Ready for production calls...")
 await asyncio.Future() # Run forever

def main():
 """Main entry point for the bot."""
 try:
 bot = OpenAIRealtimeBot()
 asyncio.run(bot.start_server())
 except KeyboardInterrupt:
 logger.info("Bot stopped by user")
 except Exception as e:
 logger.error(f"Bot failed to start: {e}")
 raise

if __name__ == "__main__":
 main() 