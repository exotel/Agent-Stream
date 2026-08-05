import os
import sys
import json
import wave
import array
import base64
import signal
import logging
import asyncio
import argparse
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from queue import Queue, Empty

import websockets
from flask import Flask, request
from flask_sock import Sock
from dotenv import load_dotenv

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


class CallLogger:
    def __init__(self, call_sid: str, stream_sid: str = None):
        self.call_sid = call_sid or f"unknown_{int(time.time())}"
        self.stream_sid = stream_sid
        self.start_time = datetime.now()

        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.filename = f"{timestamp}_{self.call_sid}.txt"
        self.filepath = os.path.join(LOGS_DIR, self.filename)

        self.logger = logging.getLogger(f"Call_{self.call_sid}")
        self.logger.setLevel(logging.DEBUG)

        # Ensure logs go to stdout for GCP Cloud Logging
        if not self.logger.handlers:
            stream_handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

        try:
            self.file_handler = logging.FileHandler(
                self.filepath, mode="w", encoding="utf-8"
            )
            self.file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            self.file_handler.setFormatter(formatter)
            self.logger.addHandler(self.file_handler)
        except Exception:
            self.file_handler = None

        self._write_header()

    def _write_header(self):
        self.logger.info("=" * 70)
        self.logger.info(f"CALL LOG - {self.call_sid}")
        self.logger.info("=" * 70)
        self.logger.info(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Stream SID: {self.stream_sid}")
        self.logger.info(f"Log File: {self.filename}")
        self.logger.info("=" * 70)

    def log(self, level: str, source: str, message: str):
        log_line = f"[{source}] {message}"
        if level == "DEBUG":
            self.logger.debug(log_line)
        elif level == "INFO":
            self.logger.info(log_line)
        elif level == "WARNING":
            self.logger.warning(log_line)
        elif level == "ERROR":
            self.logger.error(log_line)
        else:
            self.logger.info(log_line)

    def info(self, source: str, message: str):
        self.log("INFO", source, message)

    def debug(self, source: str, message: str):
        self.log("DEBUG", source, message)

    def warning(self, source: str, message: str):
        self.log("WARNING", source, message)

    def error(self, source: str, message: str):
        self.log("ERROR", source, message)

    def log_exotel(self, message: str, level: str = "INFO"):
        self.log(level, "EXOTEL", message)

    def log_elevenlabs(self, message: str, level: str = "INFO"):
        self.log(level, "ELEVENLABS", message)

    def log_bridge(self, message: str, level: str = "INFO"):
        self.log(level, "BRIDGE", message)

    def log_transcript(self, speaker: str, text: str):
        self.logger.info(f"[TRANSCRIPT] {speaker}: {text}")

    def close(self):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self.logger.info("=" * 70)
        self.logger.info("CALL ENDED")
        self.logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info("=" * 70)

        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("Bridge")
exotel_logger = logging.getLogger("Exotel")
elevenlabs_logger = logging.getLogger("ElevenLabs")

app = Flask(__name__)
sock = Sock(app)

EXOTEL_SAMPLE_RATE = 8000
EXOTEL_BIT_DEPTH = 16
EXOTEL_CHANNELS = 1
BYTES_PER_SAMPLE = EXOTEL_BIT_DEPTH // 8

CHUNK_ALIGNMENT = 320
MIN_CHUNK_SIZE = 3200
MAX_CHUNK_SIZE = 102400
DEFAULT_CHUNK_SIZE = 6400
DEFAULT_URL_AGENT_ID_FALLBACK = os.getenv(
    "DEFAULT_URL_AGENT_ID_FALLBACK", os.getenv("ELEVENLABS_AGENT_ID", "")
)


@dataclass
class BridgeConfig:
    elevenlabs_agent_id: str
    elevenlabs_api_key: str
    elevenlabs_region: str = "default"
    exotel_port: int = 10002
    audio_sample_rate: int = 8000
    chunk_size: int = DEFAULT_CHUNK_SIZE
    log_level: str = "INFO"
    bg_sound_file: str = ""
    bg_sound_volume: float = 0.3


@dataclass
class StreamMetadata:
    stream_sid: str
    call_sid: str = ""
    account_sid: str = ""
    from_number: str = ""
    to_number: str = ""
    encoding: str = "raw"
    sample_rate: int = 8000
    bit_rate: int = 16
    custom_parameters: Dict[str, str] = field(default_factory=dict)


class AudioBuffer:
    """Simple queue-based buffer for passing audio data (base64 strings) directly."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.buffer = Queue()
        self.closed = False
        self.chunk_size = chunk_size

    def put(self, data: str):
        """Put base64 audio string directly into the buffer."""
        if not self.closed and data:
            self.buffer.put(data)

    def get(self, timeout: float = 0.1) -> Optional[str]:
        """Get base64 audio string from the buffer."""
        try:
            return self.buffer.get(timeout=timeout)
        except Empty:
            return None

    def clear(self):
        """Clear all pending audio."""
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except Empty:
                break

    def flush(self):
        """No-op for compatibility."""
        pass

    def close(self):
        self.closed = True
        self.buffer.put(None)


class BackgroundSoundMixer:
    """Loads a WAV file (8kHz, 16-bit, mono) and provides looping chunks for mixing."""

    def __init__(self, filepath: str, volume: float = 0.3):
        self.volume = volume
        self.position = 0
        self.pcm_data = self._load_audio(filepath)
        self.enabled = True

    def _load_audio(self, filepath: str) -> bytes:
        with wave.open(filepath, "rb") as wf:
            if (
                wf.getnchannels() != 1
                or wf.getsampwidth() != 2
                or wf.getframerate() != 8000
            ):
                raise ValueError(
                    f"Background WAV must be 8kHz, 16-bit, mono. "
                    f"Got: {wf.getframerate()}Hz, {wf.getsampwidth() * 8}-bit, {wf.getnchannels()}ch. "
                    f"Convert with: ffmpeg -i input.mp3 -ar 8000 -ac 1 -sample_fmt s16 output.wav"
                )
            return wf.readframes(wf.getnframes())

    def get_chunk(self, num_bytes: int) -> bytes:
        """Get a chunk of background audio, looping seamlessly."""
        if not self.pcm_data or not self.enabled:
            return b"\x00" * num_bytes

        result = bytearray()
        remaining = num_bytes

        while remaining > 0:
            available = len(self.pcm_data) - self.position
            take = min(remaining, available)
            result.extend(self.pcm_data[self.position : self.position + take])
            self.position += take
            remaining -= take

            if self.position >= len(self.pcm_data):
                self.position = 0

        return bytes(result)


def mix_audio(primary: bytes, background: bytes, bg_volume: float = 0.3) -> bytes:
    """Mix two raw PCM buffers (16-bit signed LE, mono). Clips to int16 range."""
    min_len = min(len(primary), len(background))
    min_len -= min_len % 2

    samples_primary = array.array("h")
    samples_primary.frombytes(primary[:min_len])

    samples_bg = array.array("h")
    samples_bg.frombytes(background[:min_len])

    mixed = array.array(
        "h",
        [
            max(-32768, min(32767, int(p + b * bg_volume)))
            for p, b in zip(samples_primary, samples_bg)
        ],
    )

    result = mixed.tobytes()
    if len(primary) > min_len:
        result += primary[min_len:]
    return result


class ElevenLabsClient:
    REGION_URLS = {
        "default": "wss://api.elevenlabs.io",
        "us": "wss://api.us.elevenlabs.io",
        "eu": "wss://api.eu.residency.elevenlabs.io",
        "india": "wss://api.in.residency.elevenlabs.io",
    }

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        region: str = "default",
        call_logger: CallLogger = None,
    ):
        self.agent_id = agent_id
        self.api_key = api_key
        self.base_url = self.REGION_URLS.get(region, self.REGION_URLS["default"])
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.conversation_id: Optional[str] = None
        self.connected = False
        self.audio_format_out: Optional[str] = None
        self.audio_format_in: Optional[str] = None
        self.call_logger = call_logger

    @property
    def ws_url(self) -> str:
        return f"{self.base_url}/v1/convai/conversation?agent_id={self.agent_id}"

    async def connect(self) -> bool:
        try:
            extra_headers = {}
            if self.api_key:
                extra_headers["xi-api-key"] = self.api_key

            elevenlabs_logger.info("=" * 50)
            elevenlabs_logger.info("Connecting to ElevenLabs...")
            elevenlabs_logger.info(f"    URL: {self.ws_url}")
            elevenlabs_logger.info(f"    Agent ID: {self.agent_id}")
            elevenlabs_logger.info(f"    Region: {self.base_url}")
            elevenlabs_logger.info(
                f"    API Key: {'***' + self.api_key[-4:] if self.api_key else 'Not provided'}"
            )
            elevenlabs_logger.info("=" * 50)

            if self.call_logger:
                self.call_logger.log_elevenlabs(f"Connecting to ElevenLabs...")
                self.call_logger.log_elevenlabs(f"URL: {self.ws_url}")
                self.call_logger.log_elevenlabs(f"Agent ID: {self.agent_id}")

            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers=extra_headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self.connected = True
            elevenlabs_logger.info("Connected to ElevenLabs successfully!")
            if self.call_logger:
                self.call_logger.log_elevenlabs("Connected to ElevenLabs successfully!")
            return True
        except Exception as e:
            elevenlabs_logger.error(f"Failed to connect to ElevenLabs: {e}")
            if self.call_logger:
                self.call_logger.log_elevenlabs(f"Failed to connect: {e}", "ERROR")
            self.connected = False
            return False

    async def send_audio(self, audio_base64: str):
        if self.ws and self.connected:
            message = {"user_audio_chunk": audio_base64}
            elevenlabs_logger.debug(
                f">>> SEND audio chunk ({len(audio_base64)} chars base64)"
            )
            await self.ws.send(json.dumps(message))

    async def send_pong(self, event_id: int):
        if self.ws and self.connected:
            message = {"type": "pong", "event_id": event_id}
            elevenlabs_logger.debug(f">>> SEND pong (event_id: {event_id})")
            await self.ws.send(json.dumps(message))

    async def send_conversation_config(self, initiation_data: dict = None):
        """Send conversation initiation client data to ElevenLabs.

        Args:
            initiation_data: Dict containing optional fields:
                - dynamic_variables: Dict of variables accessible in agent prompt via {{var_name}}
                - conversation_config_override: Dict to override agent config (prompt, first_message, etc.)
        """
        if self.ws and self.connected:
            message = {"type": "conversation_initiation_client_data"}

            # Merge in any provided initiation data (dynamic_variables, conversation_config_override)
            if initiation_data:
                if "dynamic_variables" in initiation_data:
                    message["dynamic_variables"] = initiation_data["dynamic_variables"]
                if "conversation_config_override" in initiation_data:
                    message["conversation_config_override"] = initiation_data[
                        "conversation_config_override"
                    ]

            elevenlabs_logger.info(f">>> SEND conversation_initiation_client_data")
            elevenlabs_logger.debug(f">>> Config: {json.dumps(message, indent=2)}")
            await self.ws.send(json.dumps(message))

    async def close(self):
        elevenlabs_logger.info("Closing ElevenLabs connection...")
        self.connected = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        elevenlabs_logger.info("ElevenLabs connection closed")


class ConversationBridge:
    def __init__(self, config: BridgeConfig, agent_id_override: Optional[str] = None):
        self.config = config
        self.elevenlabs_agent_id = agent_id_override or config.elevenlabs_agent_id
        self.elevenlabs: Optional[ElevenLabsClient] = None
        self.exotel_ws = None
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.metadata: Optional[StreamMetadata] = None
        self.active = False

        self.user_audio_buffer = AudioBuffer()
        self.agent_audio_buffer = AudioBuffer(chunk_size=config.chunk_size)

        self.outbound_sequence = 0
        self.outbound_chunk = 0

        self.pending_marks: Dict[str, Any] = {}
        self.mark_counter = 0

        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.start_time: float = 0

        self.bg_mixer: Optional[BackgroundSoundMixer] = None

        self.call_logger: Optional[CallLogger] = None

    def start(self, exotel_ws, metadata: StreamMetadata):
        self.exotel_ws = exotel_ws
        self.stream_sid = metadata.stream_sid
        self.call_sid = metadata.call_sid
        self.metadata = metadata
        self.active = True
        self.start_time = time.time()

        self.call_logger = CallLogger(
            call_sid=metadata.call_sid, stream_sid=metadata.stream_sid
        )
        self.call_logger.log_exotel(f"Call started")
        self.call_logger.log_exotel(f"From: {metadata.from_number}")
        self.call_logger.log_exotel(f"To: {metadata.to_number}")
        self.call_logger.log_exotel(f"Account SID: {metadata.account_sid}")
        self.call_logger.log_exotel(
            f"Encoding: {metadata.encoding}, Sample Rate: {metadata.sample_rate}, Bit Rate: {metadata.bit_rate}"
        )
        if metadata.custom_parameters:
            self.call_logger.log_exotel(
                f"Custom Parameters: {json.dumps(metadata.custom_parameters)}"
            )

        self.outbound_sequence = 0
        self.outbound_chunk = 0
        self.mark_counter = 0

        self.user_audio_buffer = AudioBuffer()
        self.agent_audio_buffer = AudioBuffer(chunk_size=self.config.chunk_size)

        self.bg_mixer = None
        if self.config.bg_sound_file and os.path.isfile(self.config.bg_sound_file):
            try:
                self.bg_mixer = BackgroundSoundMixer(
                    self.config.bg_sound_file, self.config.bg_sound_volume
                )
                logger.info(
                    f"Background sound loaded: {self.config.bg_sound_file} "
                    f"(volume={self.config.bg_sound_volume})"
                )
                if self.call_logger:
                    self.call_logger.log_bridge(
                        f"Background sound: {self.config.bg_sound_file} "
                        f"(volume={self.config.bg_sound_volume})"
                    )
            except Exception as e:
                logger.error(f"Failed to load background sound: {e}")
                if self.call_logger:
                    self.call_logger.log_bridge(
                        f"Failed to load background sound: {e}", "ERROR"
                    )

        self.elevenlabs_thread = threading.Thread(
            target=self._run_elevenlabs_client, daemon=True
        )
        self.elevenlabs_thread.start()

        self.playback_thread = threading.Thread(
            target=self._playback_agent_audio, daemon=True
        )
        self.playback_thread.start()

        logger.info(f"Bridge started for stream: {self.stream_sid}")
        self.call_logger.log_bridge(f"Bridge started for stream: {self.stream_sid}")

    def _run_elevenlabs_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._elevenlabs_session())
        except Exception as e:
            logger.error(f"ElevenLabs session error: {e}")
        finally:
            self.loop.close()

    async def _elevenlabs_session(self):
        logger.info("Starting ElevenLabs session...")
        if self.call_logger:
            self.call_logger.log_bridge("Starting ElevenLabs session...")

        self.elevenlabs = ElevenLabsClient(
            agent_id=self.elevenlabs_agent_id,
            api_key=self.config.elevenlabs_api_key,
            region=self.config.elevenlabs_region,
            call_logger=self.call_logger,
        )

        if not await self.elevenlabs.connect():
            logger.error("Failed to establish ElevenLabs connection")
            if self.call_logger:
                self.call_logger.log_bridge(
                    "Failed to establish ElevenLabs connection", "ERROR"
                )
            return

        # Pass caller info to ElevenLabs agent as dynamic variables
        # These can be used in the agent's prompt with {{caller_number}}, {{called_number}}, etc.
        conversation_initiation_data = None
        if self.metadata:
            dynamic_vars = {
                "caller_number": self.metadata.from_number or "",
                "called_number": self.metadata.to_number or "",
                "call_sid": self.metadata.call_sid or "",
                # Add defaults for any agent-required dynamic variables
                "name": "",  # Can be overridden via custom_parameters
                "recent_history": "",  # Can be overridden via custom_parameters
            }
            # Add any custom parameters from Exotel as dynamic variables too
            if self.metadata.custom_parameters:
                dynamic_vars.update(self.metadata.custom_parameters)

            # Format per ElevenLabs docs: dynamic_variables at top level
            conversation_initiation_data = {
                "dynamic_variables": dynamic_vars,
                # Optional: Add conversation_config_override here if needed
                # "conversation_config_override": {
                #     "agent": {
                #         "first_message": "Hello! I see you're calling from {{caller_number}}.",
                #         "language": "en"
                #     }
                # }
            }
            logger.info(f"Passing dynamic variables to agent: {dynamic_vars}")
            if self.call_logger:
                self.call_logger.log_bridge(
                    f"Dynamic variables: {json.dumps(dynamic_vars)}"
                )

        await self.elevenlabs.send_conversation_config(conversation_initiation_data)

        logger.info("ElevenLabs session active - starting audio streams")
        if self.call_logger:
            self.call_logger.log_bridge(
                "ElevenLabs session active - starting audio streams"
            )

        await asyncio.gather(
            self._send_audio_to_elevenlabs(),
            self._receive_from_elevenlabs(),
            return_exceptions=True,
        )

        logger.info("ElevenLabs session ended")
        if self.call_logger:
            self.call_logger.log_bridge("ElevenLabs session ended")

        # Close Exotel WebSocket to trigger transfer flow
        # When we close, Exotel will proceed to the next applet (Connect)
        self._close_exotel_stream()

    async def _send_audio_to_elevenlabs(self):
        """Pass base64 audio directly from Exotel to ElevenLabs (no conversion)."""
        elevenlabs_logger.info(
            "Starting audio passthrough (Exotel -> ElevenLabs) [NO CONVERSION]"
        )
        chunks_sent = 0

        while self.active and self.elevenlabs and self.elevenlabs.connected:
            audio_base64 = self.user_audio_buffer.get(timeout=0.05)

            if audio_base64:
                await self.elevenlabs.send_audio(audio_base64)
                chunks_sent += 1

                if chunks_sent == 1:
                    elevenlabs_logger.info(
                        f">>> SEND - First user audio chunk sent to ElevenLabs (passthrough)"
                    )

            await asyncio.sleep(0.01)

        elevenlabs_logger.info(f"Audio passthrough stopped (sent {chunks_sent} chunks)")

    async def _receive_from_elevenlabs(self):
        elevenlabs_logger.info("Starting receiver thread (ElevenLabs -> Bridge)")
        messages_received = 0

        while self.active and self.elevenlabs and self.elevenlabs.connected:
            try:
                if self.elevenlabs.ws:
                    message = await asyncio.wait_for(
                        self.elevenlabs.ws.recv(), timeout=0.1
                    )
                    messages_received += 1
                    data = json.loads(message)
                    await self._handle_elevenlabs_message(data)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                elevenlabs_logger.info("ElevenLabs WebSocket connection closed")
                break
            except json.JSONDecodeError as e:
                elevenlabs_logger.error(f"JSON decode error: {e}")
            except Exception as e:
                elevenlabs_logger.error(f"Error receiving from ElevenLabs: {e}")
                await asyncio.sleep(0.1)

        elevenlabs_logger.info(
            f"Receiver stopped (received {messages_received} messages)"
        )

    async def _handle_elevenlabs_message(self, data: dict):
        msg_type = data.get("type")

        if msg_type != "audio":
            elevenlabs_logger.info(f"<<< RECV [{msg_type}]")
        else:
            elevenlabs_logger.debug(f"<<< RECV [{msg_type}]")

        if msg_type == "conversation_initiation_metadata":
            event = data.get("conversation_initiation_metadata_event", {})
            self.elevenlabs.conversation_id = event.get("conversation_id")
            self.elevenlabs.audio_format_out = event.get("agent_output_audio_format")
            self.elevenlabs.audio_format_in = event.get("user_input_audio_format")
            elevenlabs_logger.info(
                f"    Conversation ID: {self.elevenlabs.conversation_id}"
            )
            elevenlabs_logger.info(
                f"    Agent Output Audio Format: {self.elevenlabs.audio_format_out}"
            )
            elevenlabs_logger.info(
                f"    User Input Audio Format: {self.elevenlabs.audio_format_in}"
            )
            elevenlabs_logger.debug(f"    Full event: {json.dumps(event, indent=2)}")
            if self.call_logger:
                self.call_logger.log_elevenlabs(
                    f"Conversation ID: {self.elevenlabs.conversation_id}"
                )
                self.call_logger.log_elevenlabs(
                    f"Audio Format - Out: {self.elevenlabs.audio_format_out}, In: {self.elevenlabs.audio_format_in}"
                )

        elif msg_type == "audio":
            audio_event = data.get("audio_event", {})
            audio_base64 = audio_event.get("audio_base_64")
            event_id = audio_event.get("event_id")
            if audio_base64:
                elevenlabs_logger.debug(
                    f"    Audio chunk received (event_id: {event_id}, {len(audio_base64)} b64 chars)"
                )
                # Pass base64 directly to buffer (no conversion needed - agent uses same format as Exotel)
                self.agent_audio_buffer.put(audio_base64)

        elif msg_type == "agent_response":
            event = data.get("agent_response_event", {})
            response = event.get("agent_response", "")
            elevenlabs_logger.info(f'    Agent says: "{response}"')
            if self.call_logger:
                self.call_logger.log_transcript("AGENT", response)

        elif msg_type == "user_transcript":
            event = data.get("user_transcription_event", {})
            transcript = event.get("user_transcript", "")
            elevenlabs_logger.info(f'    User said: "{transcript}"')
            if self.call_logger:
                self.call_logger.log_transcript("USER", transcript)

        elif msg_type == "ping":
            ping_event = data.get("ping_event", {})
            event_id = ping_event.get("event_id")
            ping_ms = ping_event.get("ping_ms")
            elevenlabs_logger.debug(
                f"    Ping received (event_id: {event_id}, ping_ms: {ping_ms})"
            )
            if event_id is not None:
                await self.elevenlabs.send_pong(event_id)

        elif msg_type == "interruption":
            event = data.get("interruption_event", {})
            event_id = event.get("event_id")
            elevenlabs_logger.info(f"    User interrupted agent (event_id: {event_id})")
            if self.call_logger:
                self.call_logger.log_elevenlabs("User interrupted agent")
            self.agent_audio_buffer.clear()
            self._send_clear_to_exotel()

        elif msg_type == "agent_response_correction":
            event = data.get("agent_response_correction_event", {})
            original = event.get("original_agent_response", "")
            corrected = event.get("corrected_agent_response", "")
            elevenlabs_logger.info(f"    Agent correction:")
            elevenlabs_logger.info(f'       Original: "{original}"')
            elevenlabs_logger.info(f'       Corrected: "{corrected}"')

        elif msg_type == "client_tool_call":
            tool_call = data.get("client_tool_call", {})
            tool_name = tool_call.get("tool_name")
            tool_call_id = tool_call.get("tool_call_id")
            parameters = tool_call.get("parameters", {})
            elevenlabs_logger.info(f"    Tool call: {tool_name}")
            elevenlabs_logger.info(f"       Call ID: {tool_call_id}")
            elevenlabs_logger.info(f"       Parameters: {json.dumps(parameters)}")

        elif msg_type == "vad_score":
            event = data.get("vad_score_event", {})
            vad_score = event.get("vad_score")
            elevenlabs_logger.debug(f"    VAD score: {vad_score}")

        elif msg_type == "internal_tentative_agent_response":
            event = data.get("tentative_agent_response_internal_event", {})
            tentative = event.get("tentative_agent_response", "")
            elevenlabs_logger.debug(f'    Tentative response: "{tentative}"')

        elif msg_type == "contextual_update":
            text = data.get("text", "")
            elevenlabs_logger.info(f'    Contextual update: "{text}"')

        else:
            elevenlabs_logger.warning(f"    Unhandled message type: {msg_type}")
            elevenlabs_logger.debug(f"    Full data: {json.dumps(data, indent=2)}")

    def _send_clear_to_exotel(self):
        if self.exotel_ws and self.active:
            try:
                message = json.dumps({"event": "clear", "stream_sid": self.stream_sid})
                self.exotel_ws.send(message)
                exotel_logger.info(f">>> SEND [clear] - Clearing pending audio")
            except Exception as e:
                exotel_logger.error(f"Error sending clear to Exotel: {e}")

    def _close_exotel_stream(self):
        """Close the Exotel WebSocket to signal end of stream.

        This triggers Exotel to proceed to the next applet in the flow,
        which should be the Connect applet for call transfer.
        """
        if self.exotel_ws:
            try:
                exotel_logger.info(">>> Closing Exotel WebSocket (AI ended call)")
                exotel_logger.info(
                    ">>> This will trigger Exotel to proceed to Connect applet"
                )
                self.active = False
                # Flask-Sock uses .close() without .closed attribute
                self.exotel_ws.close()
            except Exception as e:
                exotel_logger.error(f"Error closing Exotel WebSocket: {e}")

    def _send_mark_to_exotel(self, mark_name: str):
        if self.exotel_ws and self.active:
            self.outbound_sequence += 1
            try:
                message = json.dumps(
                    {
                        "event": "mark",
                        "sequence_number": self.outbound_sequence,
                        "stream_sid": self.stream_sid,
                        "mark": {"name": mark_name},
                    }
                )
                self.exotel_ws.send(message)
                exotel_logger.debug(f">>> SEND [mark] - name: {mark_name}")
            except Exception as e:
                exotel_logger.error(f"Error sending mark to Exotel: {e}")

    def _send_media_to_exotel(self, payload_base64: str):
        """Send a media event to the Exotel WebSocket."""
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        self.outbound_sequence += 1

        message = json.dumps(
            {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": payload_base64,
                    "timestamp": str(elapsed_ms),
                    "sequenceNumber": str(self.outbound_sequence),
                },
            }
        )
        self.exotel_ws.send(message)

    def _playback_agent_audio(self):
        """Stream audio to Exotel, mixing agent speech with background sound."""
        exotel_logger.info(
            "Starting agent audio playback (with background sound mixing)"
        )

        BYTES_PER_SECOND = 16000  # 8kHz * 2 bytes per sample
        BG_CHUNK_DURATION_S = 0.02  # 20ms
        BG_CHUNK_BYTES = int(BYTES_PER_SECOND * BG_CHUNK_DURATION_S)  # 320 bytes

        # Use a shorter poll timeout when background sound is active so we
        # keep sending ambient audio even while the agent is silent.
        poll_timeout = BG_CHUNK_DURATION_S if self.bg_mixer else 0.1

        while self.active and self.exotel_ws:
            audio_base64 = self.agent_audio_buffer.get(timeout=poll_timeout)

            if audio_base64:
                try:
                    self.outbound_chunk += 1

                    if self.bg_mixer:
                        agent_bytes = base64.b64decode(audio_base64)
                        bg_bytes = self.bg_mixer.get_chunk(len(agent_bytes))
                        mixed = mix_audio(agent_bytes, bg_bytes, self.bg_mixer.volume)
                        audio_base64 = base64.b64encode(mixed).decode()

                    self._send_media_to_exotel(audio_base64)

                    if self.outbound_chunk <= 5 or self.outbound_chunk % 20 == 0:
                        exotel_logger.info(
                            f">>> SEND [media] chunk={self.outbound_chunk}, "
                            f"{len(audio_base64)} b64 chars"
                        )

                    approx_bytes = len(audio_base64) * 3 // 4
                    chunk_duration = approx_bytes / BYTES_PER_SECOND
                    time.sleep(chunk_duration * 0.9)

                except Exception as e:
                    exotel_logger.error(f"Error sending audio to Exotel: {e}")

            elif self.bg_mixer and self.bg_mixer.enabled and self.bg_mixer.volume > 0:
                # Agent is silent -- keep the ambient sound playing
                try:
                    bg_bytes = self.bg_mixer.get_chunk(BG_CHUNK_BYTES)
                    # Apply volume (bg_bytes is raw PCM, scale each sample)
                    samples = array.array("h")
                    samples.frombytes(bg_bytes)
                    vol = self.bg_mixer.volume
                    scaled = array.array(
                        "h",
                        [max(-32768, min(32767, int(s * vol))) for s in samples],
                    )
                    bg_base64 = base64.b64encode(scaled.tobytes()).decode()
                    self._send_media_to_exotel(bg_base64)
                except Exception as e:
                    exotel_logger.error(f"Error sending background audio: {e}")

        exotel_logger.info(
            f"Agent audio playback stopped (sent {self.outbound_chunk} chunks)"
        )

    def process_exotel_audio(
        self, payload: str, chunk: int = None, timestamp: str = None
    ):
        """Pass base64 audio directly to the buffer (no conversion)."""
        if self.active and payload:
            # Pass base64 directly - no decoding needed since agent uses same format
            self.user_audio_buffer.put(payload)

    def process_dtmf(self, digit: str, duration: int = None):
        exotel_logger.info(f"    DTMF digit: {digit} (duration: {duration}ms)")
        if self.call_logger:
            self.call_logger.log_exotel(f"DTMF digit: {digit} (duration: {duration}ms)")

    def handle_exotel_mark(self, mark_name: str):
        exotel_logger.info(f"    Mark completed: {mark_name}")
        if mark_name in self.pending_marks:
            del self.pending_marks[mark_name]

    def stop(self):
        logger.info(f"Stopping bridge for stream: {self.stream_sid}")
        if self.call_logger:
            self.call_logger.log_bridge(
                f"Stopping bridge for stream: {self.stream_sid}"
            )

        self.active = False

        self.agent_audio_buffer.flush()

        self.user_audio_buffer.close()
        self.agent_audio_buffer.close()

        if self.loop and self.elevenlabs:
            asyncio.run_coroutine_threadsafe(self.elevenlabs.close(), self.loop)

        if self.call_logger:
            self.call_logger.close()
            self.call_logger = None


# Global configuration
config: Optional[BridgeConfig] = None


def init_config():
    global config
    # Try to load from environment variables for cloud hosting
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if agent_id:
        config = BridgeConfig(
            elevenlabs_agent_id=agent_id,
            elevenlabs_api_key=api_key or "",
            elevenlabs_region=os.getenv("ELEVENLABS_REGION", "default"),
            exotel_port=int(os.getenv("BRIDGE_PORT", 10002)),
            chunk_size=int(os.getenv("CHUNK_SIZE", DEFAULT_CHUNK_SIZE)),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            bg_sound_file=os.getenv("BG_SOUND_FILE", ""),
            bg_sound_volume=float(os.getenv("BG_SOUND_VOLUME", "0.3")),
        )

        log_level = getattr(logging, config.log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        exotel_logger.setLevel(log_level)
        elevenlabs_logger.setLevel(log_level)
        app.logger.setLevel(log_level)


# Initialize config on module load
init_config()

active_bridges: dict = {}


def _handle_exotel_stream(ws, agent_id_override: Optional[str] = None):
    exotel_logger.info("=" * 60)
    exotel_logger.info("New WebSocket connection accepted")
    exotel_logger.info("=" * 60)
    if agent_id_override:
        exotel_logger.info(f"Using agent override from URL: {agent_id_override}")

    bridge: Optional[ConversationBridge] = None
    stream_sid: Optional[str] = None
    message_count = 0
    media_message_count = 0

    try:
        while True:
            try:
                message = ws.receive(timeout=1)
            except Exception as recv_error:
                if "closed" in str(recv_error).lower():
                    exotel_logger.info("WebSocket connection closed by remote")
                    break
                continue

            if message is None:
                continue

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                exotel_logger.warning(f"<<< RECV [INVALID JSON]: {message[:200]}...")
                continue

            event_type = data.get("event")
            sequence_number = data.get("sequence_number")
            message_count += 1

            if event_type != "media":
                exotel_logger.info(f"<<< RECV [{event_type}] seq={sequence_number}")

            if event_type == "connected":
                exotel_logger.info(f"    Protocol: {data.get('protocol', 'N/A')}")
                exotel_logger.info(f"    Version: {data.get('version', 'N/A')}")
                exotel_logger.debug(f"    Full message: {json.dumps(data, indent=2)}")

            elif event_type == "start":
                start_data = data.get("start", {})
                stream_sid = data.get("stream_sid") or start_data.get("stream_sid")

                media_format = start_data.get("media_format", {})

                sample_rate_raw = media_format.get("sample_rate", 8000)
                try:
                    sample_rate = int(
                        str(sample_rate_raw).replace("Hz", "").replace("hz", "").strip()
                    )
                except:
                    sample_rate = 8000

                bit_rate_raw = media_format.get("bit_rate", 16)
                try:
                    bit_rate_str = (
                        str(bit_rate_raw)
                        .lower()
                        .replace("kbps", "")
                        .replace("bps", "")
                        .strip()
                    )
                    bit_rate = int(bit_rate_str)
                except:
                    bit_rate = 16

                metadata = StreamMetadata(
                    stream_sid=stream_sid,
                    call_sid=start_data.get("call_sid", ""),
                    account_sid=start_data.get("account_sid", ""),
                    from_number=start_data.get("from", ""),
                    to_number=start_data.get("to", ""),
                    encoding=media_format.get("encoding", "raw"),
                    sample_rate=sample_rate,
                    bit_rate=bit_rate,
                    custom_parameters=start_data.get("custom_parameters", {}),
                )

                exotel_logger.info(f"    Stream SID: {metadata.stream_sid}")
                exotel_logger.info(f"    Call SID: {metadata.call_sid}")
                exotel_logger.info(f"    Account SID: {metadata.account_sid}")
                exotel_logger.info(f"    From: {metadata.from_number}")
                exotel_logger.info(f"    To: {metadata.to_number}")
                exotel_logger.info(
                    f"    Media Format: encoding={metadata.encoding}, sample_rate={metadata.sample_rate}, bit_rate={metadata.bit_rate}"
                )
                if metadata.custom_parameters:
                    exotel_logger.info(
                        f"    Custom Parameters: {json.dumps(metadata.custom_parameters)}"
                    )
                exotel_logger.debug(
                    f"    Full start data: {json.dumps(start_data, indent=2)}"
                )

                bridge = ConversationBridge(config, agent_id_override=agent_id_override)
                bridge.start(ws, metadata)
                active_bridges[stream_sid] = bridge

            elif event_type == "media":
                media_message_count += 1
                if bridge:
                    media_data = data.get("media", {})
                    payload = media_data.get("payload")
                    chunk = media_data.get("chunk")
                    timestamp = media_data.get("timestamp")

                    if media_message_count == 1:
                        exotel_logger.info(
                            f"<<< RECV [media] - First audio chunk received"
                        )
                        exotel_logger.info(f"    Chunk: {chunk}")
                        exotel_logger.info(f"    Timestamp: {timestamp}ms")
                        if payload:
                            decoded_size = len(base64.b64decode(payload))
                            exotel_logger.info(
                                f"    Payload: {len(payload)} base64 chars ({decoded_size} bytes)"
                            )
                    elif media_message_count % 100 == 0:
                        exotel_logger.debug(
                            f"<<< RECV [media] - Chunk #{chunk} (ts: {timestamp}ms)"
                        )

                    if payload:
                        bridge.process_exotel_audio(payload, chunk, timestamp)

            elif event_type == "dtmf":
                dtmf_data = data.get("dtmf", {})
                digit = dtmf_data.get("digit")
                duration = dtmf_data.get("duration")
                exotel_logger.info(f"    Digit: {digit}")
                exotel_logger.info(f"    Duration: {duration}ms")
                if bridge:
                    bridge.process_dtmf(digit, duration)

            elif event_type == "mark":
                mark_data = data.get("mark", {})
                mark_name = mark_data.get("name", "N/A")
                exotel_logger.info(f"    Mark name: {mark_name}")
                if bridge:
                    bridge.handle_exotel_mark(mark_name)

            elif event_type == "clear":
                exotel_logger.info(f"    Clear event received")
                if bridge:
                    bridge.agent_audio_buffer.clear()

            elif event_type == "stop":
                stop_data = data.get("stop", {})
                reason = stop_data.get("reason", "N/A")
                call_sid = stop_data.get("call_sid", "N/A")
                account_sid = stop_data.get("account_sid", "N/A")
                exotel_logger.info(f"    Reason: {reason}")
                exotel_logger.info(f"    Call SID: {call_sid}")
                exotel_logger.info(f"    Account SID: {account_sid}")
                break

            else:
                exotel_logger.warning(f"    Unknown event type: {event_type}")
                exotel_logger.debug(f"    Full data: {json.dumps(data, indent=2)}")

    except Exception as e:
        exotel_logger.error(f"Error in handler: {e}", exc_info=True)

    finally:
        if bridge:
            bridge.stop()
        if stream_sid and stream_sid in active_bridges:
            del active_bridges[stream_sid]

        exotel_logger.info("=" * 60)
        exotel_logger.info(f"Connection closed")
        exotel_logger.info(f"    Total messages: {message_count}")
        exotel_logger.info(f"    Media messages: {media_message_count}")
        exotel_logger.info("=" * 60)


# Register WebSocket routes
@sock.route("/v1/convai/conversation/exotel")
def handle_exotel_stream(ws):
    agent_id_override = (
        request.args.get("agent_id") or request.args.get("agentId") or ""
    ).strip() or DEFAULT_URL_AGENT_ID_FALLBACK
    return _handle_exotel_stream(ws, agent_id_override=agent_id_override)


@sock.route("/media")
def handle_exotel_stream_legacy(ws):
    agent_id_override = (
        request.args.get("agent_id") or request.args.get("agentId") or ""
    ).strip() or DEFAULT_URL_AGENT_ID_FALLBACK
    return _handle_exotel_stream(ws, agent_id_override=agent_id_override)


@app.route("/health")
def health_check():
    return (
        json.dumps(
            {
                "status": "healthy",
                "active_calls": len(active_bridges),
                "pending_transfers": len(pending_transfers),
                "config": {
                    "chunk_size": config.chunk_size if config else DEFAULT_CHUNK_SIZE,
                    "sample_rate": EXOTEL_SAMPLE_RATE,
                    "bg_sound_file": config.bg_sound_file if config else "",
                    "bg_sound_volume": config.bg_sound_volume if config else 0,
                },
            }
        ),
        200,
        {"Content-Type": "application/json"},
    )


# ============================================================================
# Background Sound Control
# ============================================================================


@app.route("/bg-sound", methods=["GET"])
def get_bg_sound_status():
    """Get current background sound status across all active calls."""
    statuses = {}
    for sid, bridge in active_bridges.items():
        mixer = bridge.bg_mixer
        statuses[sid] = {
            "enabled": mixer.enabled if mixer else False,
            "volume": mixer.volume if mixer else 0,
            "loaded": mixer is not None,
        }
    return (
        json.dumps({"active_calls": len(active_bridges), "calls": statuses}),
        200,
        {"Content-Type": "application/json"},
    )


@app.route("/bg-sound", methods=["POST"])
def control_bg_sound():
    """Control background sound for all active calls.

    JSON body (all fields optional):
      - enabled: bool   (start/stop)
      - volume:  float  (0.0 - 1.0)
    """
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    volume = data.get("volume")

    if enabled is None and volume is None:
        return (
            json.dumps({"error": "Provide 'enabled' (bool) and/or 'volume' (float)"}),
            400,
            {"Content-Type": "application/json"},
        )

    updated = 0
    for bridge in active_bridges.values():
        mixer = bridge.bg_mixer
        if mixer:
            if enabled is not None:
                mixer.enabled = bool(enabled)
            if volume is not None:
                mixer.volume = max(0.0, min(1.0, float(volume)))
            updated += 1

    result = {"updated_calls": updated}
    if enabled is not None:
        result["enabled"] = bool(enabled)
    if volume is not None:
        result["volume"] = volume
    logger.info(f"Background sound control: {result}")
    return json.dumps(result), 200, {"Content-Type": "application/json"}


# ============================================================================
# Transfer Management for Exotel Programmable Connect
# ============================================================================

# Store pending transfers from post-call webhooks
# Key: caller_number (from Exotel's CallFrom)
# Value: {"team_1": bool, "team_2": bool, "timestamp": float, "conversation_id": str}
pending_transfers: dict = {}

# Transfer destination phone numbers (configure via environment variables)
TRANSFER_TEAM_1_NUMBER = os.getenv("TRANSFER_TEAM_1_NUMBER", "")
TRANSFER_TEAM_2_NUMBER = os.getenv("TRANSFER_TEAM_2_NUMBER", "")
TRANSFER_TIMEOUT_SECONDS = int(
    os.getenv("TRANSFER_TIMEOUT_SECONDS", "300")
)  # 5 minutes


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to ensure consistent format for matching.

    Handles variations like:
    - +917021235464 -> 7021235464
    - 917021235464 -> 7021235464
    - 07021235464 -> 7021235464
    - 7021235464 -> 7021235464
    """
    if not phone:
        return ""

    # Remove any whitespace and non-digit chars except leading +
    cleaned = phone.strip()

    # Remove leading +
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    # Remove digits only
    cleaned = "".join(c for c in cleaned if c.isdigit())

    # Remove India country code (91) if present at start and number is long enough
    # Indian mobile numbers are 10 digits, so with 91 prefix = 12 digits
    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]

    # Remove leading zero (common in local format)
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    return cleaned


def cleanup_old_transfers():
    """Remove transfer entries older than TRANSFER_TIMEOUT_SECONDS."""
    current_time = time.time()
    expired_keys = [
        key
        for key, value in pending_transfers.items()
        if current_time - value.get("timestamp", 0) > TRANSFER_TIMEOUT_SECONDS
    ]
    for key in expired_keys:
        del pending_transfers[key]
        logger.debug(f"Cleaned up expired transfer for: {key}")


@app.route("/webhook/post-call", methods=["POST"])
def handle_post_call_webhook():
    """
    Receive post-call transcription webhook from ElevenLabs.
    Extracts data collection results to determine transfer routing.

    Expected payload structure:
    {
        "type": "post_call_transcription",
        "data": {
            "conversation_id": "...",
            "analysis": {
                "data_collection_results": {
                    "should_transfer_to_team_1": {"value": "true"/"false"},
                    "should_transfer_to_team_2": {"value": "true"/"false"}
                }
            },
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "caller_number": "...",
                    "called_number": "...",
                    "call_sid": "..."
                }
            }
        }
    }
    """
    try:
        payload = request.get_json()

        if not payload:
            logger.warning("Post-call webhook received empty payload")
            return (
                json.dumps({"status": "error", "message": "Empty payload"}),
                400,
                {"Content-Type": "application/json"},
            )

        event_type = payload.get("type")
        logger.info(f"Post-call webhook received: type={event_type}")

        if event_type != "post_call_transcription":
            logger.info(f"Ignoring non-transcription event: {event_type}")
            return (
                json.dumps({"status": "ok", "message": "Event ignored"}),
                200,
                {"Content-Type": "application/json"},
            )

        data = payload.get("data", {})
        conversation_id = data.get("conversation_id", "unknown")

        # Extract caller number from dynamic variables
        init_data = data.get("conversation_initiation_client_data", {})
        dynamic_vars = init_data.get("dynamic_variables", {})
        caller_number = dynamic_vars.get("caller_number") or dynamic_vars.get(
            "system__caller_id", ""
        )
        call_sid = dynamic_vars.get("call_sid", "")

        # Extract data collection results
        analysis = data.get("analysis", {})
        data_collection = analysis.get("data_collection_results", {})

        # Get transfer decision - single field with values: "team_1", "team_2", or "none"
        transfer_result = data_collection.get("should_transfer", {})
        transfer_value = (transfer_result.get("value") or "none").strip().lower()

        # Normalize values - accept variations like "Team 1", "team1", "team_1", etc.
        if transfer_value in (
            "team_1",
            "team1",
            "team 1",
            "existing",
            "existing_booking",
        ):
            transfer_target = "team_1"
        elif transfer_value in ("team_2", "team2", "team 2", "new", "new_booking"):
            transfer_target = "team_2"
        else:
            transfer_target = "none"

        logger.info(f"Post-call analysis for conversation {conversation_id}:")
        logger.info(f"  Caller: {caller_number}")
        logger.info(
            f"  Transfer target: {transfer_target} (raw value: {transfer_value})"
        )

        # Store transfer decision if transfer is needed
        if transfer_target != "none":
            # Clean up old entries first
            cleanup_old_transfers()

            # Normalize caller number for consistent lookup
            normalized_caller = normalize_phone_number(caller_number)

            # Use normalized caller_number as key for lookup by Programmable Connect
            if normalized_caller:
                pending_transfers[normalized_caller] = {
                    "transfer_target": transfer_target,
                    "timestamp": time.time(),
                    "conversation_id": conversation_id,
                    "call_sid": call_sid,
                    "original_number": caller_number,  # Keep original for debugging
                }
                logger.info(
                    f"Stored pending transfer for caller {caller_number} (normalized: {normalized_caller}) -> {transfer_target}"
                )
            else:
                logger.warning("No caller_number found, cannot store transfer decision")

        # Also log transcript summary if available
        transcript_summary = analysis.get("transcript_summary", "")
        if transcript_summary:
            logger.info(f"  Summary: {transcript_summary[:200]}...")

        # Forward to ticket service (elevenlabsapibot) for ticket creation
        ticket_result = None
        try:
            import requests as http_requests

            ticket_service_url = os.getenv(
                "TICKET_SERVICE_URL",
                "http://127.0.0.1:8000/api/webhook/elevenlabs-post-call",
            )
            logger.info(f"Forwarding to ticket service: {ticket_service_url}")

            # Forward original headers including ElevenLabs signature
            forward_headers = {"Content-Type": "application/json"}
            elevenlabs_sig = request.headers.get(
                "elevenlabs-signature"
            ) or request.headers.get("ElevenLabs-Signature")
            if elevenlabs_sig:
                forward_headers["elevenlabs-signature"] = elevenlabs_sig
                logger.info(f"Forwarding ElevenLabs signature header")

            # Forward the original payload with signature
            ticket_response = http_requests.post(
                ticket_service_url,
                data=request.get_data(),  # Use raw data to preserve signature
                headers=forward_headers,
                timeout=10,
            )
            ticket_result = ticket_response.json()
            logger.info(f"Ticket service response: {ticket_result}")
        except Exception as ticket_error:
            logger.warning(f"Failed to forward to ticket service: {ticket_error}")
            ticket_result = {"error": str(ticket_error)}

        return (
            json.dumps(
                {
                    "status": "ok",
                    "conversation_id": conversation_id,
                    "transfer_target": transfer_target,
                    "ticket_result": ticket_result,
                }
            ),
            200,
            {"Content-Type": "application/json"},
        )

    except Exception as e:
        logger.error(f"Error processing post-call webhook: {e}", exc_info=True)
        return (
            json.dumps({"status": "error", "message": str(e)}),
            500,
            {"Content-Type": "application/json"},
        )


@app.route("/exotel/connect", methods=["GET"])
def handle_programmable_connect():
    """
    Exotel Programmable Connect endpoint.
    Returns transfer destination based on post-call analysis.

    Exotel sends GET request with query params:
    - CallSid: Unique call identifier
    - CallFrom: Caller's number
    - CallTo: Called number (ExoPhone)
    - Direction: 'incoming' or 'outbound-dial'
    - etc.

    Returns JSON response for Programmable Connect:
    {
        "destination": {"numbers": ["+919812345678"]},
        "record": true,
        ...
    }
    """
    try:
        # Get Exotel request parameters
        call_sid = request.args.get("CallSid", "")
        call_from = request.args.get("CallFrom", "")
        call_to = request.args.get("CallTo", "")
        direction = request.args.get("Direction", "")

        logger.info(f"Programmable Connect request:")
        logger.info(f"  CallSid: {call_sid}")
        logger.info(f"  CallFrom: {call_from}")
        logger.info(f"  CallTo: {call_to}")
        logger.info(f"  Direction: {direction}")

        # Clean up old entries
        cleanup_old_transfers()

        # Normalize caller number for consistent lookup
        normalized_from = normalize_phone_number(call_from)
        logger.info(f"  Normalized CallFrom: {normalized_from}")

        # Look up pending transfer by normalized caller number
        # Wait up to 10 seconds for post-call webhook to arrive (race condition fix)
        transfer_info = None
        max_wait_seconds = 10
        poll_interval = 0.5
        waited = 0

        while waited < max_wait_seconds:
            transfer_info = pending_transfers.get(normalized_from)
            if transfer_info:
                logger.info(f"  Found transfer after {waited:.1f}s wait")
                break
            time.sleep(poll_interval)
            waited += poll_interval
            if waited < max_wait_seconds:
                logger.info(f"  Waiting for transfer... ({waited:.1f}s)")

        if not transfer_info:
            # No pending transfer found after waiting
            logger.info(
                f"No pending transfer found for {call_from} (normalized: {normalized_from}) after {max_wait_seconds}s"
            )
            return (
                json.dumps(
                    {
                        "destination": {"numbers": []},
                        "error": "No pending transfer for this caller",
                    }
                ),
                200,
                {"Content-Type": "application/json"},
            )

        # Determine transfer destination based on transfer_target
        destination_number = None
        transfer_target = transfer_info.get("transfer_target", "none")

        if transfer_target == "team_1" and TRANSFER_TEAM_1_NUMBER:
            destination_number = TRANSFER_TEAM_1_NUMBER
            logger.info(
                f"Routing {call_from} to Team 1 (existing booking): {destination_number}"
            )
        elif transfer_target == "team_2" and TRANSFER_TEAM_2_NUMBER:
            destination_number = TRANSFER_TEAM_2_NUMBER
            logger.info(
                f"Routing {call_from} to Team 2 (new booking): {destination_number}"
            )
        else:
            logger.warning(f"Transfer requested but no destination configured")
            logger.warning(f"  Transfer target: {transfer_target}")
            logger.warning(f"  Team 1 Number: {TRANSFER_TEAM_1_NUMBER}")
            logger.warning(f"  Team 2 Number: {TRANSFER_TEAM_2_NUMBER}")

        # Remove the pending transfer entry (one-time use)
        del pending_transfers[normalized_from]

        if not destination_number:
            return (
                json.dumps(
                    {
                        "destination": {"numbers": []},
                        "error": "No destination number configured for requested team",
                    }
                ),
                200,
                {"Content-Type": "application/json"},
            )

        # Return Programmable Connect response
        response = {
            "fetch_after_attempt": False,
            "destination": {"numbers": [destination_number]},
            "record": True,
            "recording_channels": "dual",
            "max_ringing_duration": 45,
            "max_conversation_duration": 3600,
            "music_on_hold": {"type": "operator_tone"},
        }

        logger.info(f"Programmable Connect response: {json.dumps(response)}")
        return json.dumps(response), 200, {"Content-Type": "application/json"}

    except Exception as e:
        logger.error(f"Error in Programmable Connect: {e}", exc_info=True)
        return (
            json.dumps({"destination": {"numbers": []}, "error": str(e)}),
            500,
            {"Content-Type": "application/json"},
        )


@app.route("/transfers", methods=["GET"])
def list_pending_transfers():
    """Debug endpoint to list pending transfers."""
    cleanup_old_transfers()
    return (
        json.dumps(
            {
                "pending_transfers": {
                    k: {
                        "team_1": v.get("team_1"),
                        "team_2": v.get("team_2"),
                        "conversation_id": v.get("conversation_id"),
                        "age_seconds": int(time.time() - v.get("timestamp", 0)),
                    }
                    for k, v in pending_transfers.items()
                },
                "config": {
                    "team_1_number": TRANSFER_TEAM_1_NUMBER or "(not configured)",
                    "team_2_number": TRANSFER_TEAM_2_NUMBER or "(not configured)",
                    "timeout_seconds": TRANSFER_TIMEOUT_SECONDS,
                },
            }
        ),
        200,
        {"Content-Type": "application/json"},
    )


def signal_handler(sig, frame):
    logger.info("Shutting down...")

    for bridge in active_bridges.values():
        bridge.stop()

    sys.exit(0)


def main():
    global config

    parser = argparse.ArgumentParser(
        description="Exotel <-> ElevenLabs Conversational AI Bridge"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("BRIDGE_PORT", 10002)),
        help="Port for the WebSocket server (default: 10002)",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default=os.getenv("ELEVENLABS_AGENT_ID"),
        help="ElevenLabs Agent ID",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("ELEVENLABS_API_KEY"),
        help="ElevenLabs API Key",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=os.getenv("ELEVENLABS_REGION", "default"),
        choices=["default", "us", "eu", "india"],
        help="ElevenLabs region (default: default)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=int(os.getenv("CHUNK_SIZE", DEFAULT_CHUNK_SIZE)),
        help=f"Audio chunk size in bytes (default: {DEFAULT_CHUNK_SIZE}, must be multiple of {CHUNK_ALIGNMENT})",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--bg-sound-file",
        type=str,
        default=os.getenv("BG_SOUND_FILE", ""),
        help="Path to background sound WAV file (8kHz, 16-bit, mono)",
    )
    parser.add_argument(
        "--bg-sound-volume",
        type=float,
        default=float(os.getenv("BG_SOUND_VOLUME", "0.3")),
        help="Background sound volume (0.0-1.0, default: 0.3)",
    )

    args = parser.parse_args()

    if args.chunk_size % CHUNK_ALIGNMENT != 0:
        parser.error(f"--chunk-size must be a multiple of {CHUNK_ALIGNMENT} bytes")
    if args.chunk_size < MIN_CHUNK_SIZE:
        parser.error(f"--chunk-size must be at least {MIN_CHUNK_SIZE} bytes")
    if args.chunk_size > MAX_CHUNK_SIZE:
        parser.error(f"--chunk-size must be at most {MAX_CHUNK_SIZE} bytes")

    if not args.agent_id:
        parser.error("--agent-id is required (or set ELEVENLABS_AGENT_ID env var)")

    if not args.api_key:
        logger.warning("No API key provided. Some features may not work.")

    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    exotel_logger.setLevel(log_level)
    elevenlabs_logger.setLevel(log_level)
    app.logger.setLevel(log_level)

    config = BridgeConfig(
        elevenlabs_agent_id=args.agent_id,
        elevenlabs_api_key=args.api_key or "",
        elevenlabs_region=args.region,
        exotel_port=args.port,
        chunk_size=args.chunk_size,
        log_level=args.log_level,
        bg_sound_file=args.bg_sound_file,
        bg_sound_volume=args.bg_sound_volume,
    )

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "=" * 60)
    print("  Exotel <-> ElevenLabs Conversational AI Bridge")
    print("=" * 60)
    print(f"  Server:      http://0.0.0.0:{args.port}")
    print(f"  WebSocket:   ws://0.0.0.0:{args.port}/v1/conversation/exotel")
    print(f"  Health:      http://0.0.0.0:{args.port}/health")
    print("-" * 60)
    print(f"  Agent ID:    {args.agent_id}")
    print(f"  Region:      {args.region}")
    print(f"  Chunk Size:  {args.chunk_size} bytes ({args.chunk_size // 16}ms @ 8kHz)")
    print(f"  Log Level:   {args.log_level}")
    if args.bg_sound_file:
        print(f"  BG Sound:    {args.bg_sound_file} (volume={args.bg_sound_volume})")
    else:
        print(f"  BG Sound:    (none)")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
