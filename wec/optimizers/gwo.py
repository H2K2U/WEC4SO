# wec/optimizers/gwo.py
"""Grey Wolf Optimizer for reservoir operation."""

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


class GreyWolfOptimizer(AbstractOptimizer):
    """Simple Grey Wolf metaheuristic.

    The algorithm searches for a vector of monthly storage changes (dV)
    that minimises squared deficits of guaranteed capacity. The search is
    performed over storage volumes at the end of each month within the
    feasible range ``[dead, NRL]``. The final volume is enforced via a
    penalty term.
    """

    def __init__(self, pack_size: int = 20, n_iter: int = 15000, seed: int = 0) -> None:
        self.pack_size = pack_size
        self.n_iter = n_iter
        self.seed = seed

    # --------------------------------------------------------------
    def compute_dV(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
    ) -> List[float]:
        rng = np.random.default_rng(self.seed)

        n_months = len(series.months)
        v_nrl = float(np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes))
        v_dead = float(np.interp(levels.dead, geom.headwater_marks, geom.average_volumes))

        # initial wolf pack: random volumes within bounds
        pack = rng.uniform(v_dead, v_nrl, size=(self.pack_size, n_months))
        # enforce final volume close to NRL
        pack[:, -1] = v_nrl

        # evaluate fitness
        scores = np.array([self._score(ind, geom, levels, series, v_nrl, v_dead) for ind in pack])

        for it in range(self.n_iter):
            # rank wolves: alpha, beta, delta are best three
            order = np.argsort(scores)
            alpha, beta, delta = pack[order[0]], pack[order[1]], pack[order[2]]

            a = 2 - 2 * it / max(1, self.n_iter - 1)
            for i in range(self.pack_size):
                for j in range(n_months):
                    r1, r2 = rng.random(), rng.random()
                    A1 = a * (2 * r1 - 1)
                    C1 = 2 * r2
                    D_alpha = abs(C1 * alpha[j] - pack[i, j])
                    X1 = alpha[j] - A1 * D_alpha

                    r1, r2 = rng.random(), rng.random()
                    A2 = a * (2 * r1 - 1)
                    C2 = 2 * r2
                    D_beta = abs(C2 * beta[j] - pack[i, j])
                    X2 = beta[j] - A2 * D_beta

                    r1, r2 = rng.random(), rng.random()
                    A3 = a * (2 * r1 - 1)
                    C3 = 2 * r2
                    D_delta = abs(C3 * delta[j] - pack[i, j])
                    X3 = delta[j] - A3 * D_delta

                    pack[i, j] = (X1 + X2 + X3) / 3

                pack[i] = np.clip(pack[i], v_dead, v_nrl)
                pack[i, -1] = v_nrl  # keep last volume fixed

            scores = np.array([self._score(ind, geom, levels, series, v_nrl, v_dead) for ind in pack])

        best = pack[np.argmin(scores)]
        volumes = np.concatenate(([v_nrl], best))
        dv = [volumes[i + 1] - volumes[i] for i in range(n_months)]
        return dv

    # --------------------------------------------------------------
    def _score(
        self,
        vols: np.ndarray,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        v_nrl: float,
        v_dead: float,
    ) -> float:
        cost = 0.0
        v_prev = v_nrl
        for t, v_end in enumerate(vols):
            v_end = np.clip(v_end, v_dead, v_nrl)
            dV = v_end - v_prev
            q = series.domestic_inflows[t] - dV * 1e9 / SECONDS_PER_MONTH
            head_start = compute_headwater_mark(v_prev, geom)
            head_end = compute_headwater_mark(v_end, geom)
            head = 0.5 * (head_start + head_end) - compute_lowwater_mark(q, geom)
            n_ges = min(compute_domestic_capacity(q, head), levels.installed_capacity)
            deficit = max(0.0, series.guaranteed_capacity[t] - n_ges)
            cost += deficit ** 2
            v_prev = v_end

        cost += 100.0 * (v_prev - v_nrl) ** 2  # penalty for imbalance
        return cost