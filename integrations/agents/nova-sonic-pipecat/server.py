#!/usr/bin/env python3
"""Amazon Nova Sonic + Pipecat on Exotel AgentStream.

Exotel (Connect Voice AI, Voicebot applet, or ExoML <StartStream>) connects to
    wss://<host>/ws?sample-rate=16000        (8000 | 16000 | 24000)
and this server bridges the call audio to Amazon Nova Sonic on Bedrock.

Pipecat handles the AgentStream events, resampling (Nova speaks at 24 kHz),
barge-in (`clear`) and Nova's ~8-minute connection limit (session continuation).
"""

import json
import os
import subprocess
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from loguru import logger

from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.exotel import ExotelFrameSerializer
from pipecat.services.aws.nova_sonic.llm import AWSNovaSonicLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

load_dotenv(override=True)

HERE = Path(__file__).parent
SUPPORTED_RATES = (8000, 16000, 24000)
DEFAULT_RATE = int(os.getenv("EXOTEL_SAMPLE_RATE", "16000"))


def system_prompt() -> str:
    if os.getenv("SYSTEM_PROMPT"):
        return os.environ["SYSTEM_PROMPT"]
    return (HERE / "system_prompt.md").read_text().strip()


def aws_credentials() -> dict:
    """AWS keys from env, else the default AWS chain (profile / SSO / EC2 or ECS role) via the aws CLI."""
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        return {
            "access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "session_token": os.getenv("AWS_SESSION_TOKEN") or None,
        }
    out = subprocess.run(
        ["aws", "configure", "export-credentials", "--format", "process"],
        capture_output=True, text=True, check=True,
    ).stdout
    c = json.loads(out)
    return {
        "access_key_id": c["AccessKeyId"],
        "secret_access_key": c["SecretAccessKey"],
        "session_token": c.get("SessionToken"),
    }


def build_llm() -> AWSNovaSonicLLMService:
    return AWSNovaSonicLLMService(
        **aws_credentials(),
        region=os.getenv("AWS_REGION", "us-east-1"),
        settings=AWSNovaSonicLLMService.Settings(
            model=os.getenv("NOVA_MODEL", "amazon.nova-2-sonic-v1:0"),
            voice=os.getenv("NOVA_VOICE", "matthew"),
            endpointing_sensitivity=os.getenv("NOVA_ENDPOINTING", "MEDIUM"),
            system_instruction=system_prompt(),
        ),
    )


def sample_rate_of(websocket: WebSocket) -> int:
    rate = int(websocket.query_params.get("sample-rate", DEFAULT_RATE))
    if rate not in SUPPORTED_RATES:
        raise ValueError(f"sample-rate {rate} not in {SUPPORTED_RATES}")
    return rate


async def run_call(websocket: WebSocket, llm) -> None:
    rate = sample_rate_of(websocket)
    # Reads AgentStream `connected` + `start` (stream_sid, call_sid, custom_parameters).
    _, call_data = await parse_telephony_websocket(websocket)
    call_sid = call_data["call_id"]
    logger.info(f"call start: call_sid={call_sid} stream_sid={call_data['stream_id']} rate={rate}")

    serializer = ExotelFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_sid,
        params=ExotelFrameSerializer.InputParams(audio_in_sample_rate=rate, audio_out_sample_rate=rate),
    )
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
            # AgentStream wants outbound media >= 100 ms and a multiple of 320 bytes.
            # 10 ms of PCM16 mono is 160/320/480 B at 8/16/24 kHz, so pick N x 10 ms
            # giving >= 3200 B: 20 at 8 kHz (3200 B), 10 at 16 kHz (3200 B), 10 at 24 kHz (4800 B).
            audio_out_10ms_chunks=20 if rate == 8000 else 10,
        ),
    )

    context = LLMContext([{"role": "system", "content": system_prompt()}])
    agg = LLMContextAggregatorPair(context)

    pipeline = Pipeline([transport.input(), agg.user(), llm, transport.output(), agg.assistant()])
    task = PipelineTask(
        pipeline,
        params=PipelineParams(audio_in_sample_rate=rate, audio_out_sample_rate=rate),
    )

    @transport.event_handler("on_client_connected")
    async def _greet(_t, _c):
        await task.queue_frames([LLMRunFrame()])  # bot speaks first

    @transport.event_handler("on_client_disconnected")
    async def _bye(_t, _c):
        logger.info(f"call end: call_sid={call_sid}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.add_workers(task)
    await runner.run()


app = FastAPI()


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    await run_call(websocket, build_llm())


@app.get("/health")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8765")),
    )
