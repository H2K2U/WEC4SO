# wec/optimizers/__init__.py
"""Базовые абстракции и фабрика оптимизаторов ΔV.

*Модуль объединяет:*
1. **AbstractOptimizer** — абстрактный базовый класс (ABC), определяющий
   единый интерфейс ``compute_dV`` для всех стратегий планирования
   сработки/наполнения.
2. Функцию‑фабрику **get(name)**, возвращающую экземпляр оптимизатора
   по строковому алиасу ("greedy", "dynamic", ...). Это упрощает создание
   оптимизаторов из конфигов или CLI‑аргументов.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries

# ---------------------------------------------------------------------------
# Абстрактный базовый класс оптимизаторов
# ---------------------------------------------------------------------------


class AbstractOptimizer(ABC):
    """Интерфейс любой стратегии подбора годовых ΔV_t (км³).

    Метод ``compute_dV`` должен возвращать **список из 12 чисел**, где
    отрицательные значения означают *сработку* (уменьшение объёма
    водохранилища), а положительные — *наполнение*.
    """

    @abstractmethod
    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List,  # список OperationMode, но импорт избегаем, чтобы не создавать циклы
    ) -> List[float]:
        """Вернуть годовой план ΔV (длина == len(series) == 12)."""
        ...


# ---------------------------------------------------------------------------
# Фабрика оптимизаторов по строковому имени
# ---------------------------------------------------------------------------


def get(name: str = "greedy") -> AbstractOptimizer:
    """Вернуть готовый объект‑оптимизатор по алиасу *name*.

    Parameters
    ----------
    name : str
        Допустимые значения по умолчанию:
        * ``"greedy"``  – GreedyOptimizer,
        * ``"dynamic"`` – DynamicOptimizer.

    Raises
    ------
    ValueError
        Если передано неизвестное имя оптимизатора.
    """
    if name == "greedy":
        from .greedy import GreedyOptimizer

        return GreedyOptimizer()
    if name == "dynamic":
        from .dynamic import DynamicOptimizer

        return DynamicOptimizer()

    raise ValueError(f"Unknown optimizer '{name}'")
