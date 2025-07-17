# wec/facade/analyzer.py

import pandas as pd
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..core.month_selector import MonthSelector
from ..core.reservoir_simulator import ReservoirSimulator
from ..visualization import plots

class WECAnalyzer:
    """High‑level entry point for clients."""
    def __init__(self, geom: Geometry, levels: StaticLevels,
                 series: HydrologicalSeries):
        self.g, self.lvl, self.s = geom, levels, series

    def simulate(self) -> pd.DataFrame:
        sel = MonthSelector(self.s, self.g, self.lvl)
        rot_series, modes = sel.rotated()
        sim = ReservoirSimulator(self.g, self.lvl, rot_series, modes)
        return sim.run()

    # thin wrappers to plotting helpers
    def plot_domestic_inflow(self): plots.plot_domestic_inflow(self.s)
    def plot_guaranteed_capacity(self): plots.plot_guaranteed_capacity(self.s)
    def plot_reservoir_levels(self, df: pd.DataFrame):
        plots.plot_reservoir_levels(df, self.lvl)
