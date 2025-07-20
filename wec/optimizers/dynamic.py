# wec/optimizers/dynamic.py
"""Dynamic programming search over storage states.

The reservoir volume at the beginning of a month is treated as the DP
state.  The algorithm discretises the feasible interval between the
`dead` level and `NRL` in 0.1km³ steps and explores all transitions.
A squared penalty is added whenever the guaranteed capacity is not
met.  Only transitions that respect volume bounds and the installed
capacity constraint are considered.
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
    """Simple discrete dynamic programming reservoir optimizer."""

    def __init__(self, step: float = 0.1) -> None:
        self.step = step

    # --------------------------------------------------------------
    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
    ) -> List[float]:
        n_months = len(series.months)
        nrl_volume = float(
            np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes)
        )
        dead_volume = float(
            np.interp(levels.dead, geom.headwater_marks, geom.average_volumes)
        )
        grid = np.arange(dead_volume, nrl_volume + self.step / 2, self.step)
        n_states = len(grid)

        inf = float("inf")
        cost = np.full((n_months + 1, n_states), inf)
        prev = np.full((n_months, n_states), -1, dtype=int)

        start_idx = int(round((nrl_volume - dead_volume) / self.step))
        cost[0, start_idx] = 0.0

        for t in range(n_months):
            q_byt = series.domestic_inflows[t]
            n_gar = series.guaranteed_capacity[t]
            for i, v in enumerate(grid):
                if cost[t, i] == inf:
                    continue
                for j, vn in enumerate(grid):
                    dV = vn - v
                    q = q_byt - dV * 1e9 / SECONDS_PER_MONTH
                    start_h = compute_headwater_mark(v, geom)
                    end_h = compute_headwater_mark(vn, geom)
                    head = 0.5 * (start_h + end_h) - compute_lowwater_mark(q, geom)
                    n_ges = min(
                        compute_domestic_capacity(q, head),
                        levels.installed_capacity,
                    )
                    deficit = max(0.0, n_gar - n_ges)
                    new_cost = cost[t, i] + deficit ** 2
                    if new_cost < cost[t + 1, j]:
                        cost[t + 1, j] = new_cost
                        prev[t, j] = i

        end_idx = start_idx
        if cost[n_months, end_idx] == inf:
            end_idx = int(np.argmin(cost[n_months]))

        states = [end_idx]
        for t in range(n_months - 1, -1, -1):
            states.append(prev[t, states[-1]])
        states.reverse()
        volumes = [grid[i] for i in states]

        return [volumes[t + 1] - volumes[t] for t in range(n_months)]
