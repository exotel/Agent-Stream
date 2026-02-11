"""
Compatibility shim for Python versions where stdlib `audioop` is unavailable.

This project uses `audioop.ratecv` for PCM16 mono resampling between
8k/16k/24k (Exotel) and 16k/24k (Gemini Live).

This implementation provides a minimal subset:
  - ratecv(fragment, width, nchannels, inrate, outrate, state) -> (out, new_state)

Notes:
  - Supports only 16-bit (width=2) mono (nchannels=1).
  - Uses linear interpolation resampling (good enough for integration testing).
  - `state` is preserved to avoid clicks across chunk boundaries.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple
import struct
import math


RatecvState = Tuple[int, float]  # (last_sample, fractional_position)


def ratecv(
    fragment: bytes,
    width: int,
    nchannels: int,
    inrate: int,
    outrate: int,
    state: Optional[RatecvState],
) -> tuple[bytes, RatecvState]:
    if width != 2 or nchannels != 1:
        raise NotImplementedError("audioop shim supports only PCM16 mono (width=2, nchannels=1)")
    if inrate <= 0 or outrate <= 0:
        raise ValueError("inrate/outrate must be > 0")
    if not fragment:
        return b"", state or (0, 0.0)

    # Decode little-endian int16 samples
    n = len(fragment) // 2
    samples = struct.unpack("<" + "h" * n, fragment[: n * 2])

    last_sample, frac_pos = state if state is not None else (samples[0], 0.0)

    # Prepend last sample to improve continuity across chunks
    src = (last_sample,) + samples
    src_len = len(src)

    ratio = outrate / inrate
    # Compute output sample count based on source (excluding the prepended sample)
    out_len = max(1, int((src_len - 1) * ratio))

    out = []
    for i in range(out_len):
        # Map output index to source position (skip the prepended sample offset)
        pos = (i / ratio) + frac_pos
        idx0 = int(pos)
        if idx0 >= src_len - 1:
            s = src[-1]
        else:
            idx1 = idx0 + 1
            s0 = src[idx0]
            s1 = src[idx1]
            t = pos - idx0
            s = int((1.0 - t) * s0 + t * s1)
        out.append(max(-32768, min(32767, s)))

    # New state: last real source sample + leftover fractional position
    # frac_pos should keep the fractional remainder beyond the last consumed source sample
    total_src_advanced = (out_len / ratio) + frac_pos
    frac_pos_new = total_src_advanced - math.floor(total_src_advanced)
    new_state: RatecvState = (samples[-1], frac_pos_new)

    return struct.pack("<" + "h" * len(out), *out), new_state

