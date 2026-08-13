"""Agent session for speechmatics-gpt-elevenlabs-native.

STT is implemented here (batch Jobs API) because the shared
``stt_speechmatics`` helper is intentionally a no-op placeholder.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import audioop
import httpx
from dotenv import load_dotenv

load_dotenv()

from integrations.agents._shared.pipeline_agent import PipelineSession
from integrations.agents._shared.providers import llm_openai, tts_elevenlabs

SPEECHMATICS_BATCH_URL = os.getenv(
    "SPEECHMATICS_BATCH_URL",
    "https://asr.api.speechmatics.com/v2/jobs",
)


def _wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _to_16k(pcm: bytes, sample_rate: int) -> tuple[bytes, int]:
    if sample_rate == 16000:
        return pcm, 16000
    out, _ = audioop.ratecv(pcm, 2, 1, sample_rate, 16000, None)
    return out, 16000


async def stt_speechmatics_batch(pcm: bytes, sample_rate: int) -> str:
    """Speechmatics Batch STT via Jobs API (WAV upload + poll).

    Docs: https://docs.speechmatics.com/speech-to-text/batch/quickstart
    """
    key = os.environ["SPEECHMATICS_API_KEY"]
    pcm16, rate = _to_16k(pcm, sample_rate)
    language = os.getenv("SPEECHMATICS_LANGUAGE", "en")
    operating_point = os.getenv("SPEECHMATICS_MODEL", "enhanced")
    config = {
        "type": "transcription",
        "transcription_config": {
            "language": language,
            "operating_point": operating_point,
        },
    }
    base = SPEECHMATICS_BATCH_URL.rstrip("/")

    async with httpx.AsyncClient(timeout=120.0) as client:
        create = await client.post(
            f"{base}/",
            headers={"Authorization": f"Bearer {key}"},
            data={"config": json.dumps(config)},
            files={"data_file": ("audio.wav", _wav_bytes(pcm16, rate), "audio/wav")},
        )
        create.raise_for_status()
        job_id = create.json()["id"]

        while True:
            st = await client.get(
                f"{base}/{job_id}",
                headers={"Authorization": f"Bearer {key}"},
            )
            st.raise_for_status()
            body = st.json()
            status = (body.get("job") or body).get("status")
            if status == "done":
                break
            if status == "rejected":
                raise RuntimeError(f"Speechmatics job rejected: {body}")
            await asyncio.sleep(0.5)

        tr = await client.get(
            f"{base}/{job_id}/transcript",
            headers={"Authorization": f"Bearer {key}"},
            params={"format": "txt"},
        )
        tr.raise_for_status()
        ctype = tr.headers.get("content-type", "")
        if "application/json" in ctype:
            payload = tr.json()
            parts: list[str] = []
            for item in payload.get("results") or []:
                for alt in item.get("alternatives") or []:
                    content = alt.get("content")
                    if content:
                        parts.append(content)
            return " ".join(parts).strip()
        return (tr.text or "").strip()


def make_session(stream_sid: str, sample_rate: int, call_meta: dict) -> PipelineSession:
    return PipelineSession(
        stream_sid,
        sample_rate,
        call_meta,
        stt=stt_speechmatics_batch,
        llm=llm_openai,
        tts=tts_elevenlabs,
    )
