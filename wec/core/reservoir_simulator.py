# wec/core/reservoir_simulator.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from .month_selector import OperationMode
from .formulas import (
    compute_headwater_mark,
    compute_lowwater_mark,
    compute_domestic_capacity,
)
from .interpolation import Interpolator, default_interp
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..constants import SECONDS_PER_MONTH
from ..optimizers import AbstractOptimizer, get as get_optimizer

logger = logging.getLogger(__name__)


@dataclass
class ReservoirState:
    """Текущее состояние водохранилища в цикле моделирования."""
    volume: float  # км³


class ReservoirSimulator:
    """
    Месячный (T = 12) прогон режима водохранилища.

    Логика расчёта помесячных изменений объёма (ΔV) вынесена в объект‑стратегию
    `optimizer`, реализующий интерфейс `AbstractOptimizer`. Это позволяет
    «горячо» подставлять разные алгоритмы (greedy, pyomo‑NLP, MILP, …),
    не трогая вычисление энергетических показателей и форма͏т выходной таблицы.
    """

    # ------------------------------------------------------------------
    def __init__(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
        optimizer: AbstractOptimizer | str = "greedy",
        interp: Interpolator = default_interp,
    ) -> None:
        if len(series.months) != len(modes):
            raise ValueError("Length of hydrological series and modes must match.")

        self.geom = geom
        self.levels = levels
        self.series = series
        self.modes = modes
        self.optimizer = (
            get_optimizer(optimizer) if isinstance(optimizer, str) else optimizer
        )
        self.interp = interp

        # постоянные объёмы при НПУ/УМО
        self._nrl_volume = float(
            np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes)
        )
        self._dead_volume = float(
            np.interp(levels.dead, geom.headwater_marks, geom.average_volumes)
        )

    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        """Возвращает подробную таблицу ВЭР за год."""
        logger.info("Starting reservoir simulation …")
        state = ReservoirState(volume=self._nrl_volume)
        records: list[dict] = []

        # 1️⃣ Получить весь план ΔV (уже со знаком)
        dv_plan = self.optimizer.compute_dV(
            self.geom, self.levels, self.series, self.modes
        )

        # 2️⃣ Последовательно симулировать месяцы
        for i, month in enumerate(self.series.months):
            mode = self.modes[i]
            dV   = dv_plan[i]  # сработка >0, наполнение <0  (договорённость)

            q_byt = self.series.domestic_inflows[i]
            n_gar = self.series.guaranteed_capacity[i]

            start_vol = state.volume
            end_vol   = start_vol + dV
            start_head = compute_headwater_mark(start_vol, self.geom, self.interp)
            end_head   = compute_headwater_mark(end_vol,   self.geom, self.interp)
            avg_head   = 0.5 * (start_head + end_head)

            # вклад водохранилища в расход ГЭС
            res_delta_q = (- dV * 1e9) / SECONDS_PER_MONTH  # м³/с
            plant_q = q_byt + res_delta_q

            z_low   = compute_lowwater_mark(plant_q, self.geom, self.interp)
            pressure = avg_head - z_low
            n_byt = compute_domestic_capacity(q_byt, pressure)
            n_ges    = min(compute_domestic_capacity(plant_q, pressure),
                           self.levels.installed_capacity)

            logger.debug("month=%2d mode=%s dV=%.3f Vend=%.3f N=%.1f",
                         month, mode.name, dV, end_vol, n_ges)

            records.append(
                {
                    "Месяц": month,
                    "Режим": str(mode),
                    "Q_быт, м³/с": q_byt,
                    "Q_вдх, м³/с": res_delta_q,
                    "Q_ГЭС, м³/с": plant_q,
                    "dV, км³": dV,
                    "V_вдх_нач, км³": start_vol,
                    "V_вдх_кон, км³": end_vol,
                    "Z_вб_нач, м": start_head,
                    "Z_вб_кон, м": end_head,
                    "Z_нб, м": z_low,
                    "H, м": pressure,
                    "N_быт, МВт": n_byt,
                    "N_гар, МВт": n_gar,
                    "N_ГЭС, МВт": n_ges,
                }
            )
            state.volume = end_vol  # переход к следующему месяцу

        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 0)
        return pd.DataFrame.from_records(records)
