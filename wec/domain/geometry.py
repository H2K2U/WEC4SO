# wec/domain/geometry.py

from dataclasses import dataclass
from typing import List

@dataclass(slots=True)
class Geometry:
    """Hydraulic geometry of the reservoir & river reach."""
    headwater_marks: List[float]              # Zвб (м)
    average_volumes: List[float]              # Vср (км³)
    lowwater_marks: List[float]               # Zнб (м)
    lowwater_inflows: List[float]             # Qнб (м³/с)
