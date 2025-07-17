# wec/core/reservoir_simulator.py

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

logger = logging.getLogger(__name__)

@dataclass
class ReservoirState:
    """Mutable state of reservoir for the simulation loop."""
    volume: float  # км³

class ReservoirSimulator:
    """Forward model for one hydrological year with monthly resolution."""

    def __init__(
        self,
        geom: Geometry,
        levels: StaticLevels,
        series: HydrologicalSeries,
        modes: List[OperationMode],
        interp: Interpolator = default_interp,
    ) -> None:
        if len(series.months) != len(modes):
            raise ValueError("Length of hydrological series and modes must match.")
        self.geom = geom
        self.levels = levels
        self.series = series
        self.modes = modes
        self.interp = interp

        # Pre‑compute static numbers
        self._nrl_volume = float(np.interp(levels.nrl, geom.headwater_marks, geom.average_volumes))

    # -------public API --------------------------------------------------
    def run(self) -> pd.DataFrame:
        """Return a dataframe with month‑by‑month reservoir & plant metrics."""
        logger.info("Starting reservoir simulation …")
        state = ReservoirState(volume=self._nrl_volume)
        records: list[dict] = []

        # Split indexes by mode for nicer logic below
        fill_indices = [i for i, m in enumerate(self.modes) if m is OperationMode.FILL]
        discharge_indices = [i for i, m in enumerate(self.modes) if m is OperationMode.DISCHARGE]

        # Compute discharge volumes so each month meets guaranteed capacity
        discharge_volumes = self._calc_discharge_volumes(state.volume, discharge_indices)

        # Evenly spread that volume across fill months (then fine‑tune)
        fill_volumes = self._initial_fill_distribution(sum(discharge_volumes), fill_indices)
        fill_volumes = self._balance_fill_months(fill_volumes, fill_indices, discharge_volumes, state.volume)

        # Simulate sequentially (one pass)
        for i, month in enumerate(self.series.months):
            q_byt = self.series.domestic_inflows[i]
            n_gar = self.series.guaranteed_capacity[i]
            mode = self.modes[i]
            dV = discharge_volumes.pop(0) if mode is OperationMode.DISCHARGE else fill_volumes.pop(0)

            start_volume = state.volume
            end_volume = start_volume - dV if mode is OperationMode.DISCHARGE else start_volume + dV
            start_head = compute_headwater_mark(start_volume, self.geom, self.interp)
            end_head = compute_headwater_mark(end_volume, self.geom, self.interp)
            avg_head = 0.5 * (start_head + end_head)

            reservoir_delta_flow = (dV * 1e9) / SECONDS_PER_MONTH  # m³/s
            plant_inflow = q_byt + reservoir_delta_flow if mode is OperationMode.DISCHARGE else q_byt - reservoir_delta_flow
            z_low = compute_lowwater_mark(plant_inflow, self.geom, self.interp)
            pressure = avg_head - z_low
            n_ges = compute_domestic_capacity(plant_inflow, pressure)
            n_ges = min(n_ges, self.levels.installed_capacity)

            # log once per month if desired
            logger.debug("m=%s mode=%s dV=%.2f km³ N=%.1f MW", month, mode, dV, n_ges)

            records.append(
                {
                    "Месяц": month,
                    "Режим": str(mode),
                    "Q_быт, м³/с": q_byt,
                    "dV, км³": dV if mode is OperationMode.DISCHARGE else -dV,
                    "V_вдх_нач, км³": start_volume,
                    "V_вдх_кон, км³": end_volume,
                    "Z_вб_нач, м": start_head,
                    "Z_вб_кон, м": end_head,
                    "Z_нб, м": z_low,
                    "H, м": pressure,
                    "N_гар, МВт": n_gar,
                    "N_ГЭС, МВт": n_ges,
                }
            )
            state.volume = end_volume  # advance state
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 0)

        return pd.DataFrame.from_records(records)

    # -------private helpers ---------------------------------------------
    def _calc_discharge_volumes(self, start_volume: float, d_indices: List[int]) -> List[float]:
        """Iteratively raise dV for each discharge month until N≥1.05·Nгар."""
        volumes: List[float] = [0.0 for _ in d_indices]
        for k, idx in enumerate(d_indices):
            q_byt = self.series.domestic_inflows[idx]
            n_gar = self.series.guaranteed_capacity[idx]
            dV = 0.0
            while True:
                reservoir_delta_flow = (dV * 1e9) / SECONDS_PER_MONTH
                plant_inflow = q_byt + reservoir_delta_flow
                z_low = compute_lowwater_mark(plant_inflow, self.geom)
                avg_head = self.levels.nrl - z_low  # close approx; dV small per iteration
                n_ges = compute_domestic_capacity(plant_inflow, avg_head)
                n_ges = min(n_ges, self.levels.installed_capacity)
                if n_ges >= 1.05 * n_gar: break
                dV += 0.01  # км³ step
            volumes[k] = dV
            start_volume -= dV  # mutate for consecutive months
        return volumes

    @staticmethod
    def _initial_fill_distribution(total_discharge: float, fill_indices: List[int]) -> List[float]:
        if not fill_indices: return []
        even_share = total_discharge / len(fill_indices)
        return [even_share for _ in fill_indices]

    def _balance_fill_months(
        self,
        fill_volumes: List[float],
        fill_indices: List[int],
        discharge_volumes: List[float],
        start_volume: float,
    ) -> List[float]:
        """Very similar to original iterative balancing loop, but more explicit."""
        if not fill_indices: return []
        volumes = fill_volumes.copy()
        plant_caps = self._recompute_fill_capacities(volumes, fill_indices, start_volume)
        for i, idx in enumerate(fill_indices):
            n_gar = self.series.guaranteed_capacity[idx]
            while plant_caps[i] < 1.05 * n_gar and volumes[i] >= 0.01:
                j = int(np.argmax(plant_caps))
                volumes[j] += 0.01
                volumes[i] -= 0.01
                # update only two changed months for efficiency
                plant_caps[i] = self._calc_fill_capacity_single(volumes[i], idx, start_volume)
                plant_caps[j] = self._calc_fill_capacity_single(volumes[j], fill_indices[j], start_volume)
        return volumes

    # -- helper for balancing
    def _recompute_fill_capacities(self, volumes: List[float], indices: List[int], start_volume: float) -> List[float]:
        caps: List[float] = []
        vol = start_volume
        for dV, idx in zip(volumes, indices):
            q_byt = self.series.domestic_inflows[idx]
            vol_end = vol + dV
            avg_head = 0.5 * (
                compute_headwater_mark(vol, self.geom) + compute_headwater_mark(vol_end, self.geom)
            )
            reservoir_delta_flow = (dV * 1e9) / SECONDS_PER_MONTH
            plant_inflow = q_byt - reservoir_delta_flow
            z_low = compute_lowwater_mark(plant_inflow, self.geom)
            caps.append(compute_domestic_capacity(plant_inflow, avg_head - z_low))
            vol = vol_end
        return caps

    def _calc_fill_capacity_single(self, dV: float, idx: int, start_volume: float) -> float:
        q_byt = self.series.domestic_inflows[idx]
        vol_end = start_volume + dV
        avg_head = 0.5 * (
            compute_headwater_mark(start_volume, self.geom) + compute_headwater_mark(vol_end, self.geom)
        )
        reservoir_delta_flow = (dV * 1e9) / SECONDS_PER_MONTH
        plant_inflow = q_byt - reservoir_delta_flow
        z_low = compute_lowwater_mark(plant_inflow, self.geom)
        return compute_domestic_capacity(plant_inflow, avg_head - z_low)
