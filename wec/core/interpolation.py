# wec/core/interpolation.py

from typing import Protocol, Sequence
import numpy as np

class Interpolator(Protocol):
    """A minimal interface for 1‑D interpolation, so we can inject mocks.
    Any object satisfying ``__call__(x, xp, fp) -> float`` qualifies.
    """

    def __call__(self, x: float | np.ndarray, xp: Sequence[float], fp: Sequence[float]) -> float:  # noqa: E501
        ...


def default_interp(x: float | np.ndarray, xp: Sequence[float], fp: Sequence[float]) -> float:  # noqa: E501
    """Thin wrapper around :func:`numpy.interp` so that we can unit‑test easily."""
    return float(np.interp(x, xp, fp))
