# wec/core/formulas.py

from .interpolation import Interpolator, default_interp
from ..domain.geometry import Geometry

def compute_lowwater_mark(q: float, geom: Geometry, interp: Interpolator = default_interp) -> float:
    """Return Zнб (м) by interpolating Q‑Z rating curve."""
    return interp(q, geom.lowwater_inflows, geom.lowwater_marks)


def compute_headwater_mark(volume: float, geom: Geometry, interp: Interpolator = default_interp) -> float:
    """Return Zвб (м) for given storage volume by V‑Z curve."""
    return interp(volume, geom.average_volumes, geom.headwater_marks)


def compute_domestic_capacity(q: float, h: float) -> float:
    """Бытовая мощность (МВт) по расходу и напору.

    Formula: *N* = 8.5 × Q × H / 1000.
    """
    return 8.5 * q * h / 1000.0
