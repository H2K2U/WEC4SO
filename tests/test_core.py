import importlib

MonthSelector = importlib.import_module('wec.core.month_selector').MonthSelector
OperationMode = importlib.import_module('wec.core.month_selector').OperationMode
Greedy = importlib.import_module('wec.optimizers.greedy').GreedyOptimizer
ReservoirSimulator = importlib.import_module('wec.core.reservoir_simulator').ReservoirSimulator


def test_month_selector_modes(hydro_series, geometry, static_levels):
    selector = MonthSelector(hydro_series, geometry, static_levels)
    modes = selector.calc_modes()
    names = [m.name for m in modes]
    expected = [
        'DISCHARGE', 'DISCHARGE', 'DISCHARGE', 'FILL', 'FILL',
        'DISCHARGE', 'FILL', 'FILL', 'FILL',
        'DISCHARGE', 'DISCHARGE', 'DISCHARGE'
    ]
    assert names == expected


def test_greedy_zero_sum(hydro_series, geometry, static_levels):
    selector = MonthSelector(hydro_series, geometry, static_levels)
    modes = selector.calc_modes()
    dv = Greedy().compute_dV(geometry, static_levels, hydro_series, modes)
    assert abs(sum(dv)) < 1e-6


def test_simulator_installed_capacity(hydro_series, geometry, static_levels):
    selector = MonthSelector(hydro_series, geometry, static_levels)
    modes = selector.calc_modes()
    sim = ReservoirSimulator(geometry, static_levels, hydro_series, modes, Greedy())
    df = sim.run()
    assert max(df['N_ГЭС, МВт']) <= static_levels.installed_capacity + 1e-9
