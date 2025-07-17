# wec/core/month_selector.py

import logging
from enum import Enum, auto
from typing import List, Sequence, Tuple

from ..domain.hydrological_series import HydrologicalSeries
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from .interpolation import Interpolator, default_interp
from .formulas import compute_lowwater_mark, compute_domestic_capacity

logger = logging.getLogger(__name__)

class OperationMode(Enum):
    FILL = auto()       # "наполнение"
    DISCHARGE = auto()  # "сработка"

    def __str__(self) -> str:  # nicer print
        return "наполнение" if self is OperationMode.FILL else "сработка"


class MonthSelector:
    """Determine the first *discharge* month and rotate series accordingly."""

    def __init__(self, series: HydrologicalSeries, geom: Geometry, levels: StaticLevels, interp: Interpolator = default_interp):
        self._s = series
        self._geom = geom
        self._levels = levels
        self._interp = interp

    def calc_modes(self) -> List[OperationMode]:
        """Return monthly mode list without rotation.

        A month is in *DISCHARGE* mode when *Nбыт* < *Nгар* (±1 МВт guard)."""
        modes: List[OperationMode] = []
        nrl_level = self._levels.nrl
        for q_byt, n_gar in zip(self._s.domestic_inflows, self._s.guaranteed_capacity):
            z_low = compute_lowwater_mark(q_byt, self._geom, self._interp)
            head = nrl_level - z_low
            n_byt = compute_domestic_capacity(q_byt, head) + 1  # +1 МВт margin vs rounding
            mode = OperationMode.DISCHARGE if n_byt < n_gar else OperationMode.FILL
            modes.append(mode)
        for i in range(1, len(modes) - 1):
            if (
                modes[i - 1] is OperationMode.DISCHARGE
                and modes[i]     is OperationMode.FILL
                and modes[i + 1] is OperationMode.DISCHARGE
            ):
                modes[i] = OperationMode.DISCHARGE   # превращаем «ложное» наполнение в сработку
        return modes

    def rotated(self) -> Tuple[HydrologicalSeries, List[OperationMode]]:
        """Rotate so that first *DISCHARGE* month after August (index > 8) starts year."""
        modes = self.calc_modes()
        try:
            start_idx = next(i for i, m in enumerate(modes) if m is OperationMode.DISCHARGE and i > 8)
        except StopIteration:
            logger.warning("No discharge month found after September; keeping original order.")
            return self._s, modes

        def _rot(lst: Sequence):
            return list(lst[start_idx:]) + list(lst[:start_idx])

        rotated_series = HydrologicalSeries(
            months=_rot(self._s.months),
            domestic_inflows=_rot(self._s.domestic_inflows),
            guaranteed_capacity=_rot(self._s.guaranteed_capacity),
        )
        rotated_modes = _rot(modes)
        return rotated_series, rotated_modes
