"""Minimal numpy stubs for testing without external dependency."""

__version__ = '0.0'
ndarray = list

from typing import Sequence, Any

# Simple linear interpolation

def interp(x: float, xp: Sequence[float], fp: Sequence[float]) -> float:
    if x <= xp[0]:
        return float(fp[0])
    for i in range(1, len(xp)):
        if x <= xp[i]:
            x0, x1 = xp[i-1], xp[i]
            y0, y1 = fp[i-1], fp[i]
            return float(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return float(fp[-1])

def argmax(seq: Sequence[Any]) -> int:
    max_idx = 0
    max_val = seq[0]
    for i, v in enumerate(seq):
        if v > max_val:
            max_val = v
            max_idx = i
    return max_idx
