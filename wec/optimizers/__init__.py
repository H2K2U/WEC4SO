# wec/optimizers/__init__.py
from abc import ABC, abstractmethod
from typing import List
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries

class AbstractOptimizer(ABC):
    """Интерфейс любой стратегии подбора ΔV_t."""
    @abstractmethod
    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List,
    ) -> List[float]: ...

# фабрика для удобства
def get(name: str = "greedy") -> AbstractOptimizer:
    if name == "greedy":
        from .greedy import GreedyOptimizer
        return GreedyOptimizer()
    if name == "pyomo":
        from .pyomo_optimizer import PyomoOptimizer
        return PyomoOptimizer()
    if name == "dynamic":
        from .dynamic import DynamicOptimizer
        return DynamicOptimizer()
    if name == "gwo":
        from .gwo import GreyWolfOptimizer
        return GreyWolfOptimizer()
    raise ValueError(f"Unknown optimizer '{name}'")
