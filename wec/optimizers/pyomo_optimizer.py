from __future__ import annotations

from typing import List
import pyomo.environ as pyo

from . import AbstractOptimizer
from ..core.optimizer import optimise_year
from ..core.month_selector import OperationMode
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries


class PyomoOptimizer(AbstractOptimizer):
    """Wrapper that builds and solves a Pyomo model."""

    def __init__(self, solver: str = "cbc") -> None:
        self.solver = solver

    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
    ) -> List[float]:
        model = optimise_year(
            geom,
            levels,
            series,
            modes,
            solver=self.solver,
        )
        dv = [pyo.value(model.dV[t]) for t in model.T]
        return dv

