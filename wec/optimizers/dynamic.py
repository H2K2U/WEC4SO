# wec/optimizers/dynamic.py
"""
Динамическое программирование (ДП) для годового управления водохранилищем.

Идея метода
-----------
1. **Состояние** S_t – объём воды в водохранилище в НАЧАЛЕ t‑го месяца.
   Диапазон возможных объёмов ограничен двумя уровнями:
   - УМО (уровень мёртвого объёма)  → минимальный допустимый объём;
   - НПУ (нормальный подпорный уровень) → максимальный объём.

   Между этими границами строится равномерная дискретная сетка (шаг `step`, км³).
   Это делает задачу конечной и позволяет применить ДП.

2. **Управление** ΔV_t = V_{t+1} – V_t  (км³):
   - если месяц помечен как «сработка» (DISCHARGE) – объём должен уменьшаться (ΔV ≤ 0);
   - если «наполнение» (FILL) – объём растёт (ΔV ≥ 0).

3. **Целевая функция – лексикографическая** (двойной приоритет):
   1) Сначала минимизируем суммарный дефицит мощности за год:
        D = Σ max(0, N_гар(t) − N_ГЭС(t)).
   2) Среди решений с одинаковым D минимизируем отрицательную энергию (т.е. максимизируем выработку):
        E = Σ N_ГЭС(t) * τ,  τ – длительность месяца в часах.
      В коде используется «−E», чтобы и первый, и второй критерии можно было минимизировать.

4. **Ограничения**:
   - Мощность агрегатов ограничена установленной мощностью N_inst.
   - Z_вб (уровень верхнего бьефа) не опускается ниже УМО.
   - Поддерживается правило «две фазы» (знак ΔV согласован с режимом месяца).

Результат – вектор ΔV длиной 12 месяцев, который даёт оптимальную траекторию объёмов.

Почему два критерия?
--------------------
Системный оператор прежде всего обязан обеспечить гарантированную мощность (надёжность).
Только если дефицита нет (или он минимален и дальше уменьшить нельзя), имеет смысл «выжимать» энергию.
Лексикографическое сравнение делает именно это: сравниваются сначала дефициты, и только
при равенстве – энергии.

"""

from __future__ import annotations

from typing import List
import numpy as np

from . import AbstractOptimizer
from ..core.formulas import (
    compute_headwater_mark,   # Z_вб(V): уровень верхнего бьефа по объёму
    compute_lowwater_mark,    # Z_нб(Q): уровень нижнего бьефа по расходу
    compute_domestic_capacity # N(Q, H): «бытовая» формула мощности
)
from ..constants import SECONDS_PER_MONTH
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..core.month_selector import OperationMode


class DynamicOptimizer(AbstractOptimizer):
    """ДП‑оптимизатор ΔV с лексикографической целью (минимум дефицита → максимум энергии)."""

    def __init__(self, step: float = 0.1) -> None:
        """
        Parameters
        ----------
        step : float
            Шаг дискретизации объёма водохранилища (км³).
            Чем меньше шаг, тем точнее, но тем больше время расчёта.
        """
        self.step = step

    # ------------------------------------------------------------------ #
    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
    ) -> List[float]:
        """Возвращает оптимальный план ΔV на 12 месяцев (км³/месяц)."""

        n_months = len(series.months)

        # ---- 1. Преобразуем уровни в объёмы (используем среднюю кривую V(Z)) ----
        nrl_volume  = float(np.interp(levels.nrl,  geom.headwater_marks, geom.average_volumes))
        dead_volume = float(np.interp(levels.dead, geom.headwater_marks, geom.average_volumes))

        # ---- 2. Строим дискретную сетку состояний по объёму ----
        step = self.step
        grid = np.arange(dead_volume, nrl_volume + step, step)
        # Страхуемся от накопления ошибок округления:
        grid[0]  = dead_volume
        grid[-1] = min(grid[-1], nrl_volume)
        n_states = len(grid)

        # ---- 3. Инициализация таблиц ДП ----
        INF = float("inf")
        # def_cost[t, i] – минимальный суммарный дефицит к концу месяца t при объёме grid[i]
        def_cost = np.full((n_months + 1, n_states), INF)
        # en_cost[t, i]  – суммарная «отрицательная» энергия (−E) при том же условии
        en_cost  = np.full((n_months + 1, n_states), INF)
        # prev[t, i]     – индекс состояния в месяце t−1, из которого оптимально пришли в (t, i)
        prev     = np.full((n_months,     n_states), -1, dtype=int)

        # Старт: в начале года водохранилище в НПУ
        start_idx = int(np.argmin(np.abs(grid - nrl_volume)))
        def_cost[0, start_idx] = 0.0
        en_cost[0,  start_idx] = 0.0

        # ---- 4. Главный цикл Беллмана: перебор месяцев и переходов ----
        for t in range(n_months):
            q_byt = series.domestic_inflows[t]   # бытовая приточность (м³/с)
            n_gar = series.guaranteed_capacity[t]# гарантированная мощность (МВт)
            mode  = modes[t]                     # режим месяца (сработка/наполнение)

            for i, v in enumerate(grid):
                if def_cost[t, i] == INF:
                    continue  # это состояние недостижимо

                z_start = compute_headwater_mark(v, geom)

                for j, vn in enumerate(grid):
                    dV = vn - v  # управление
                    # 4.1 Ограничение знака ΔV (режим)
                    if (mode is OperationMode.DISCHARGE and dV > 0.0) or \
                       (mode is OperationMode.FILL       and dV < 0.0):
                        continue

                    z_end = compute_headwater_mark(vn, geom)
                    # 4.2 Не опускаться ниже УМО
                    if z_start < levels.dead - 1e-9 or z_end < levels.dead - 1e-9:
                        continue

                    # 4.3 Гидравлика/энергия
                    # Расход через ГЭС: приток + вклад водохранилища (ΔV/τ)
                    q     = q_byt - dV * 1e9 / SECONDS_PER_MONTH
                    z_low = compute_lowwater_mark(q, geom)
                    head  = 0.5 * (z_start + z_end) - z_low

                    n_ges   = min(compute_domestic_capacity(q, head), levels.installed_capacity)
                    deficit = max(0.0, n_gar - n_ges)   # штрафуем только недобор
                    energy  = n_ges * SECONDS_PER_MONTH / 3600.0  # МВт·ч за месяц

                    # 4.4 Обновление стоимости (лексикографически)
                    new_def = def_cost[t, i] + deficit
                    new_en  = en_cost[t,  i] - energy  # «минус», чтобы тоже минимизировать

                    # Принцип сравнения: сначала деф., затем энергия
                    better = (
                        new_def < def_cost[t + 1, j] or
                        (np.isclose(new_def, def_cost[t + 1, j]) and new_en < en_cost[t + 1, j])
                    )
                    if better:
                        def_cost[t + 1, j] = new_def
                        en_cost[t + 1,  j] = new_en
                        prev[t, j]         = i

        # ---- 5. Восстановление оптимальной траектории ----
        end_idx = start_idx
        if def_cost[n_months, end_idx] == INF:
            # теоретически не должно случиться, но на всякий случай берём лучший
            end_idx = int(np.argmin(def_cost[n_months]))

        states = [end_idx]
        for t in range(n_months - 1, -1, -1):
            states.append(prev[t, states[-1]])
        states.reverse()

        volumes = [grid[idx] for idx in states]
        # Возвращаем ΔV_t = V_{t+1} − V_t
        return [volumes[t + 1] - volumes[t] for t in range(n_months)]
