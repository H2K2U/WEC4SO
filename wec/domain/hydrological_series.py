# wec/domain/hydrological_series.py

from dataclasses import dataclass
from typing import List

@dataclass(slots=True)
class HydrologicalSeries:
    """Time‑series forcing for a hydrological year (monthly)."""

    months: List[int]                  # 1‥12
    domestic_inflows: List[float]      # Qбыт (м³/с)
    guaranteed_capacity: List[float]   # Nгар (МВт)

    def __post_init__(self) -> None:  # quick sanity
        if not (len(self.months) == len(self.domestic_inflows) == len(self.guaranteed_capacity)):
            raise ValueError("All hydrological time‑series must have equal length.")
