# wec/core/reservoir_simulator.py
"""Модуль пошаговой (месячной) симуляции водохранилища.

* Принимает на вход:
  - геометрию гидроузла (кривые V–Z, Q–Z, установленная мощность),
  - статические уровни (НПУ, УМО, установл. мощность),
  - гидрологический ряд (месяц → приточность, гарантированная мощность),
  - список режимов работы (сработка / наполнение),
  - объект‑оптимизатор, который рассчитывает план сработки/наполнения
    (ΔV) на весь год.
* На выходе формируется **DataFrame** со всеми промежуточными
  величинами: расходы, уровни, напоры, мощности.

Таким образом, модуль отделяет *генерацию управлений* (за которую
отвечает оптимизатор) от *моделирования последствий* этих управлений
(энергетический результат, уровни). Это позволяет легко тестировать и
сравнивать разные алгоритмы при одинаковой «физике» водохранилища.
"""

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

# ---------------------------------------------------------------------------
# Состояние водохранилища на данный месяц
# ---------------------------------------------------------------------------


@dataclass
class ReservoirState:
    """Минимальный контейнер для хранения текущего объёма."""

    volume: float  # км³ – объём воды в начале месяца


# ---------------------------------------------------------------------------
# Основной класс симулятора
# ---------------------------------------------------------------------------


class ReservoirSimulator:
    """Помесячная (T = 12) симуляция работы водохранилища.

    Шаги работы:
    1. Оптимизатор выдаёт список ΔV (км³) длиной 12
       (отрицательные – сработка, положительные – наполнение).
    2. Симулятор последовательно применяет эти ΔV, считая уровни,
       напоры, расходы и мощности.
    3. Результаты аккумулируются в таблицу, пригодную для анализа
       (вывод в PDF/Excel, построение графиков, проверка KPI).
    """

    # ------------------------------------------------------------------
    # Конструктор
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
        # Проверка согласованности входов
        if len(series.months) != len(modes):
            raise ValueError(
                "Length of hydrological series and modes must match."
            )

        self.geom = geom
        self.levels = levels
        self.series = series
        self.modes = modes
        # Позволяем передавать либо строку‑алиас, либо уже созданный объект
        self.optimizer = (
            get_optimizer(optimizer) if isinstance(optimizer, str) else optimizer
        )
        self.interp = interp

        # Предрассчитываем объёмы, соответствующие НПУ и УМО
        self._nrl_volume = float(
            np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes)
        )
        self._dead_volume = float(
            np.interp(levels.dead, geom.headwater_marks, geom.average_volumes)
        )

    # ------------------------------------------------------------------
    # Главная точка входа симуляции
    # ------------------------------------------------------------------

    def run(self) -> pd.DataFrame:
        """Запустить годовую симуляцию и вернуть подробный DataFrame."""
        logger.info("Starting reservoir simulation …")

        # Начальное состояние – водоём заполнен до НПУ
        state = ReservoirState(volume=self._nrl_volume)
        records: list[dict] = []  # накопитель строк отчёта

        # 1) Получаем план ΔV от оптимизатора (уже со знаком!)
        dv_plan = self.optimizer.compute_dV(
            self.geom, self.levels, self.series, self.modes
        )

        # 2) Пошаговая симуляция
        for i, month in enumerate(self.series.months):
            mode = self.modes[i]
            dV = dv_plan[i]  # <0 – сработка, >0 – наполнение

            # ----- исходные данные за месяц -----
            q_byt = self.series.domestic_inflows[i]  # приток (м³/с)
            n_gar = self.series.guaranteed_capacity[i]  # гарант. мощность (МВт)

            # ----- геометрия/уровни -----
            start_vol = state.volume  # объём на начало месяца
            end_vol = start_vol + dV  # объём на конец месяца
            # пересчитываем отметки верхнего бьефа
            start_head = compute_headwater_mark(start_vol, self.geom, self.interp)
            end_head = compute_headwater_mark(end_vol, self.geom, self.interp)
            avg_head = 0.5 * (start_head + end_head)

            # ----- перерасход/дополнительный расход из/в водохранилище -----
            res_delta_q = (-dV * 1e9) / SECONDS_PER_MONTH  # м³/с
            plant_q = q_byt + res_delta_q  # итоговый расход через турбины

            # ----- отметка нижнего бьефа и напор -----
            z_low = compute_lowwater_mark(plant_q, self.geom, self.interp)
            pressure = avg_head - z_low  # нетто‑напор

            # ----- мощности -----
            n_byt = compute_domestic_capacity(q_byt, pressure)
            n_ges = min(
                compute_domestic_capacity(plant_q, pressure),
                self.levels.installed_capacity,
            )

            logger.debug(
                "month=%2d mode=%s dV=%.3f Vend=%.3f N=%.1f",
                month,
                mode.name,
                dV,
                end_vol,
                n_ges,
            )

            # ----- запись строки отчёта -----
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

            # Переходим к следующему месяцу
            state.volume = end_vol

        # 3) Сводим результаты в DataFrame
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 0)
        return pd.DataFrame.from_records(records)
