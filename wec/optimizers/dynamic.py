# wec/optimizers/dynamic.py
"""Динамическое программирование для годового управления водохранилищем.

Алгоритм рассматривает **объём водохранилища в начале месяца** как
состояние DP. Диапазон между УМО и НПУ дискретизируется равномерным
шагом (по умолчанию 0.1 км³). Для каждого месяца перебираются все
переходы *v → vₙ*, рассчитывается дефицит мощности и кумулятивная
стоимость.  Целевая функция — **сумма квадратов дефицита гарантированной
мощности**. Квадрат подчёркивает нежелательность недоотпуска и в то же
время оставляет задачу аддитивной, что и требуется для метода
Беллмана.

Особенности реализации
----------------------
* Итоговый годовой цикл должен начаться и закончиться на объёме НПУ.
  Если идеально замкнуть цикл не удалось (стоимость = ∞), выбирается
  ближайшее по стоимости конечное состояние.
* Ограничение по установленной мощности учитывается via ``min( N_расч,
  N_inst )``.
* ``modes`` (сработка/наполнение) не влияют на DP — они передаются для
  совместимости, но логика динамики сама определяет допустимые ΔV.
"""

from __future__ import annotations

from typing import List

import numpy as np

from . import AbstractOptimizer
from ..core.formulas import (
    compute_headwater_mark,
    compute_lowwater_mark,
    compute_domestic_capacity,
)
from ..constants import SECONDS_PER_MONTH
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..core.month_selector import OperationMode


class DynamicOptimizer(AbstractOptimizer):
    """Простой оптимизатор на базе дискретного ДП."""

    def __init__(self, step: float = 0.1) -> None:
        # Шаг дискретизации объёма, км³ (0.1 даёт ~1% точность при V≈10‑20)
        self.step = step

    # ------------------------------------------------------------------
    # Основной метод интерфейса AbstractOptimizer
    # ------------------------------------------------------------------

    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],  # не используется, сохраняем сигнатуру
    ) -> List[float]:
        n_months = len(series.months)

        # --- расчёт границ объёма ---
        nrl_volume = float(
            np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes)
        )
        dead_volume = float(
            np.interp(levels.dead, geom.headwater_marks, geom.average_volumes)
        )

        # --- дискретная сетка состояний ---
        grid = np.arange(dead_volume, nrl_volume + self.step / 2, self.step)
        n_states = len(grid)

        # --- инициализация матриц DP ---
        inf = float("inf")
        cost = np.full((n_months + 1, n_states), inf)
        prev = np.full((n_months, n_states), -1, dtype=int)  # хранит индекс пред. сост.

        start_idx = int(round((nrl_volume - dead_volume) / self.step))
        cost[0, start_idx] = 0.0  # начинаем год при НПУ без штрафа

        # ------------------------------------------------------------------
        # Основной цикл Беллмана: t → t+1
        # ------------------------------------------------------------------

        for t in range(n_months):
            q_byt = series.domestic_inflows[t]
            n_gar = series.guaranteed_capacity[t]

            for i, v in enumerate(grid):
                if cost[t, i] == inf:  # недостижимое состояние
                    continue

                for j, vn in enumerate(grid):
                    dV = vn - v  # управление (км³); + наполнение, - сработка

                    # Расход через турбины с учётом ΔV
                    q = q_byt - dV * 1e9 / SECONDS_PER_MONTH

                    # Нетто‑напор (средний за месяц)
                    start_h = compute_headwater_mark(v, geom)
                    end_h = compute_headwater_mark(vn, geom)
                    head = 0.5 * (start_h + end_h) - compute_lowwater_mark(q, geom)

                    # Мощности
                    n_ges = min(
                        compute_domestic_capacity(q, head),
                        levels.installed_capacity,
                    )
                    deficit = max(0.0, n_gar - n_ges)

                    new_cost = cost[t, i] + deficit**2
                    if new_cost < cost[t + 1, j]:
                        cost[t + 1, j] = new_cost
                        prev[t, j] = i  # запоминаем оптимальный переход

        # ------------------------------------------------------------------
        # Восстановление оптимальной траектории
        # ------------------------------------------------------------------

        end_idx = start_idx  # хотим вернуться в НПУ
        if cost[n_months, end_idx] == inf:
            # Если не получилось строго вернуться — берём лучшее доступное
            end_idx = int(np.argmin(cost[n_months]))

        states = [end_idx]
        for t in range(n_months - 1, -1, -1):
            states.append(prev[t, states[-1]])
        states.reverse()
        volumes = [grid[i] for i in states]

        # ΔV_t = V_{t+1} – V_t (длина = 12)
        return [volumes[t + 1] - volumes[t] for t in range(n_months)]
