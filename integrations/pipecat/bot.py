"""
Pipecat pipeline for Exotel AgentStream (STT → LLM → TTS).

Uses ExotelFrameSerializer via FastAPIWebsocketParams / create path in server.py.
Default: Deepgram + OpenAI + Cartesia @ 8 kHz PCM (same pattern as Pipecat Twilio telephony).

Greeting: boot-cached Cartesia PCM (same voice as turn TTS) for near-0 first media.
"""

from __future__ import annotations

import os
import time

from loguru import logger
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import OutputAudioRawFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from greeting_cache import get_cached_greeting_pcm
from voice_config import (
    ENCODING,
    SAMPLE_RATE,
    cartesia_model,
    cartesia_voice_id,
    greeting_text,
)


async def run_bot(transport: BaseTransport, *, handle_sigint: bool = False) -> None:
    """Run one call session on an already-configured Exotel WebSocket transport."""
    # Faster than default gpt-4.1 for voice turns; keep replies short.
    llm_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAILLMService.Settings(
            model=llm_model,
            system_instruction=(
                "You are a helpful voice assistant on a phone call. "
                "Keep replies to one short sentence. Do not use special characters "
                "that are awkward when spoken aloud."
            ),
        ),
    )

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        ttfs_p99_latency=0.25,
    )

    # Same voice / model / rate / encoding as greeting_cache (voice_config).
    # SENTENCE aggregation (Pipecat/Cartesia default): natural prosody.
    # Do NOT use TOKEN + max_buffer_delay_ms=0 — Cartesia flushes each token
    # with leading silence → "hello..........how......" on the phone.
    voice = cartesia_voice_id()
    tts_model = cartesia_model()
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        sample_rate=SAMPLE_RATE,
        encoding=ENCODING,
        settings=CartesiaTTSService.Settings(
            model=tts_model,
            voice=voice,
        ),
    )

    # Match Pipecat telephony defaults (Twilio guide uses 8 kHz + responsive VAD).
    vad = SileroVADAnalyzer(
        params=VADParams(
            confidence=0.7,
            start_secs=0.2,
            stop_secs=0.2,
            min_volume=0.6,
        )
    )

    # Default Smart Turn stop_secs=3.0 added ~3s dead air; keep sub-second.
    smart_turn_stop = float(os.getenv("SMART_TURN_STOP_SECS", "0.8"))
    turn_analyzer = LocalSmartTurnAnalyzerV3(
        params=SmartTurnParams(stop_secs=smart_turn_stop),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=vad,
            user_turn_strategies=UserTurnStrategies(
                stop=[
                    TurnAnalyzerUserTurnStopStrategy(turn_analyzer=turn_analyzer),
                ]
            ),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            # Twilio telephony guide: avoid resample by matching 8 kHz end-to-end.
            audio_in_sample_rate=SAMPLE_RATE,
            audio_out_sample_rate=SAMPLE_RATE,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        text = greeting_text()
        context.add_message({"role": "assistant", "content": text})

        cached = get_cached_greeting_pcm()
        if cached:
            t0 = time.perf_counter()
            await worker.queue_frames(
                [
                    OutputAudioRawFrame(
                        audio=cached,
                        sample_rate=SAMPLE_RATE,
                        num_channels=1,
                    )
                ]
            )
            logger.info(
                f"Exotel client connected — cached greeting voice={voice} "
                f"text={text!r} bytes={len(cached)} "
                f"queue_ms={(time.perf_counter() - t0) * 1000:.1f} "
                f"llm={llm_model} smart_turn_stop={smart_turn_stop}"
            )
            return

        logger.warning("Greeting cache miss — live TTSSpeakFrame fallback")
        await worker.queue_frames([TTSSpeakFrame(text)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Exotel client disconnected")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=handle_sigint)
    await runner.add_workers(worker)
    await runner.run()
