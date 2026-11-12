"""Offline test: no AWS, no phone call. Run: python test_offline.py

Swaps Nova Sonic for a fake that echoes the caller's audio as 24 kHz bot audio
(Nova's output rate) and barges in once, then plays a fake Exotel client and checks:
  - outbound `media` carries our stream_sid
  - every outbound chunk is >= 3200 B and a multiple of 320 B (Exotel's rule)
  - a barge-in produces a `clear` event
"""

import asyncio
import base64
import json
import math
import struct
import threading
import time

import numpy as np
import uvicorn
import websockets
from fastapi import WebSocket

import server as bot
from pipecat.frames.frames import Frame, InputAudioRawFrame, TTSAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

PORT = 8765
RATES = (8000, 16000, 24000)


class FakeNova(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.n = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            self.n += 1
            # upsample to 24 kHz like Nova's output, so the resample path is exercised
            pcm = np.frombuffer(frame.audio, dtype=np.int16)
            up = np.interp(np.linspace(0, len(pcm), int(len(pcm) * 24000 / frame.sample_rate), endpoint=False),
                           np.arange(len(pcm)), pcm).astype(np.int16)
            await self.push_frame(TTSAudioRawFrame(audio=up.tobytes(), sample_rate=24000, num_channels=1))
            if self.n == 60:
                await self.broadcast_interruption()
        else:
            await self.push_frame(frame, direction)


@bot.app.websocket("/test")
async def test_ws(websocket: WebSocket):
    await websocket.accept()
    await bot.run_call(websocket, FakeNova())


def tone(ms: int, rate: int) -> bytes:
    n = rate * ms // 1000
    return b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))


async def fake_exotel(RATE: int):
    sizes, clears, sids = [], 0, set()
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/test?sample-rate={RATE}") as ws:
        await ws.send(json.dumps({"event": "connected"}))
        await ws.send(json.dumps({"event": "start", "sequence_number": 1, "stream_sid": "SID123",
                                  "start": {"stream_sid": "SID123", "call_sid": "CALL123", "account_sid": "acc",
                                            "from": "+910000000000", "to": "+910000000001", "custom_parameters": {},
                                            "media_format": {"encoding": "base64", "sample_rate": str(RATE), "bit_rate": "128kbps"}}}))

        async def reader():
            nonlocal clears
            try:
                async for raw in ws:
                    m = json.loads(raw)
                    if m.get("event") == "media":
                        sids.add(m["stream_sid"])
                        sizes.append(len(base64.b64decode(m["media"]["payload"])))
                    elif m.get("event") == "clear":
                        clears += 1
            except websockets.ConnectionClosed:
                pass

        rt = asyncio.create_task(reader())
        chunk = tone(20, RATE)
        for i in range(150):  # 3 s of caller audio in 20 ms frames
            await ws.send(json.dumps({"event": "media", "sequence_number": i + 2, "stream_sid": "SID123",
                                      "media": {"chunk": i + 1, "timestamp": str(i * 20),
                                                "payload": base64.b64encode(chunk).decode()}}))
            await asyncio.sleep(0.02)
        await asyncio.sleep(2)
        await ws.send(json.dumps({"event": "stop", "stream_sid": "SID123", "stop": {"reason": "callended"}}))
        await ws.close()
        rt.cancel()
    return sizes, clears, sids


def main():
    server = uvicorn.Server(uvicorn.Config(bot.app, host="127.0.0.1", port=PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(1.5)
    all_ok = True
    for rate in RATES:
        sizes, clears, sids = asyncio.run(fake_exotel(rate))
        bad = [s for s in sizes if s < 3200 or s % 320]
        ok = len(sizes) > 10 and not bad and clears >= 1 and sids == {"SID123"}
        all_ok &= ok
        print(f"{rate} Hz: media chunks={len(sizes)} sizes={sorted(set(sizes))} bad={len(bad)} "
              f"clears={clears} -> {'ok' if ok else 'FAIL'}")
    server.should_exit = True
    print("PASS" if all_ok else "FAIL")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
