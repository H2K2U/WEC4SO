# wec/facade/analyzer.py
"""Высокоуровневый *facade* для запуска расчётов и построения графиков.

Класс **WECAnalyzer** инкапсулирует последовательность вызовов:
1. Определение последовательности месяцев (MonthSelector).
2. Оптимизация ΔV + симуляция (ReservoirSimulator).
3. (опц.) Визуализация результатов через модуль *visualization.plots*.

Таким образом, клиентскому коду достаточно создать один объект
**WECAnalyzer** и вызвать ``simulate`` – всё остальное делается «под
капотом». Серия тонких обёрток ``plot_*`` предоставляет быстрый доступ
к базовым графикам без повторения boilerplate‑кода.
"""

from __future__ import annotations

import pandas as pd

from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..core.month_selector import MonthSelector
from ..core.reservoir_simulator import ReservoirSimulator
from ..optimizers import AbstractOptimizer
from ..visualization import plots


class WECAnalyzer:
    """Единая точка входа для внешних пользователей библиотеки WEC."""

    # ------------------------------------------------------------------
    # Конструктор
    # ------------------------------------------------------------------

    def __init__(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
    ) -> None:
        self.g = geom
        self.lvl = levels
        self.s = series

    # ------------------------------------------------------------------
    # Основной публичный метод
    # ------------------------------------------------------------------

    def simulate(
        self,
        optimizer: str | AbstractOptimizer = "greedy",
    ) -> pd.DataFrame:
        """Запустить оптимизацию + симуляцию и вернуть таблицу результатов."""
        # 1. Формируем режимы/поворачиваем год
        sel = MonthSelector(self.s, self.g, self.lvl)
        rot_s, modes = sel.rotated()

        # 2. Запускаем симулятор с выбранным оптимизатором
        sim = ReservoirSimulator(
            self.g, self.lvl, rot_s, modes, optimizer=optimizer
        )
        return sim.run()

    # ------------------------------------------------------------------
    # Быстрые обёртки для графиков
    # ------------------------------------------------------------------

    def plot_domestic_inflow(self):
        """График помесячных бытовых притоков."""
        plots.plot_domestic_inflow(self.s)

    def plot_guaranteed_capacity(self):
        """График гарантированной мощности."""
        plots.plot_guaranteed_capacity(self.s)

    def plot_reservoir_levels(self, df: pd.DataFrame):
        """График уровней водохранилища по результатам симуляции."""
        plots.plot_reservoir_levels(df, self.lvl)
