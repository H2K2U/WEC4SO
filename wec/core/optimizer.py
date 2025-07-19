# wec/core/optimizer.py
from __future__ import annotations

import numpy as np
import pyomo.environ as pyo
from pyomo.environ import Piecewise

from ..constants import SECONDS_PER_MONTH
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from ..domain.hydrological_series import HydrologicalSeries
from ..core.month_selector import OperationMode


def optimise_year(
    geom: Geometry,
    levels: StaticLevels,
    series: HydrologicalSeries,
    modes: list[OperationMode],           # ← передаём список режимов
    safety: float = 1.00,                 # запас к N_гар
    solver: str | None = None,            # имя решателя Pyomo (CBC, GLPK, ...)
) -> pyo.ConcreteModel:
    """
    Нелинейная модель ``max Σ N_ГЭС``.

    * ``safety·N_гар ≤ N_ГЭС ≤ N_уст``;
    * ``Z_УМО ≤ Z_вб ≤ Z_НПУ`` (в последний месяц сработки ``Z_вб = Z_УМО``);
    * ``Σ ΔV = 0``.

    Если указан ``solver``, модель будет сразу решена и
    возвращена в решённом состоянии.
    """
    T, dt = len(series.months), SECONDS_PER_MONTH

    V_nrl  = float(np.interp(levels.nrl,  geom.headwater_marks, geom.average_volumes))
    V_dead = float(np.interp(levels.dead, geom.headwater_marks, geom.average_volumes))
    dV_amp = V_nrl - V_dead

    # индекс последнего месяца DISCHARGE
    try:
        t_dead = max(i+1 for i, m in enumerate(modes) if m is OperationMode.DISCHARGE)
    except ValueError:
        t_dead = 1                                     # если сработки нет — первый месяц

    m = pyo.ConcreteModel("WEC‑NLP")
    m.T = pyo.RangeSet(1, T)

    # ------------ параметры -------------
    m.V_NRL  = pyo.Param(initialize=V_nrl)
    m.V_DEAD = pyo.Param(initialize=V_dead)

    Q_byt = {t: series.domestic_inflows[t-1]    for t in m.T}
    P_gar = {t: series.guaranteed_capacity[t-1] for t in m.T}

    # ------------ переменные ------------
    m.dV = pyo.Var(m.T, bounds=(-dV_amp, dV_amp))               # км³
    m.V  = pyo.Var(m.T, bounds=(m.V_DEAD, m.V_NRL))       # км³
    m.Q  = pyo.Var(m.T, bounds=(0, geom.lowwater_inflows[-1]))
    m.Z_up  = pyo.Var(m.T)
    m.Z_up_prev = pyo.Var(m.T)                            # Z_вб начала месяца
    m.Z_low = pyo.Var(m.T)
    m.P = pyo.Var(m.T, bounds=(0, levels.installed_capacity))

    # -------- Z_вб = f(V) -------------
    Piecewise(
        m.T, m.Z_up, m.V,
        pw_pts=geom.average_volumes,
        f_rule=dict(enumerate(geom.headwater_marks)),
        pw_constr_type="EQ", pw_repn="BIGM",
    )

    # -------- Z_нб = g(Q) -------------
    pts_q  = [0] + geom.lowwater_inflows
    pts_zl = [geom.lowwater_marks[0]] + geom.lowwater_marks
    Piecewise(
        m.T, m.Z_low, m.Q,
        pw_pts=pts_q,
        f_rule=dict(enumerate(pts_zl)),
        pw_constr_type="EQ", pw_repn="BIGM",
    )

    # -------- баланс объёма -----------
    def _bal(mdl, t):
        return mdl.V[t] == (mdl.V_NRL + mdl.dV[t] if t == 1
                            else mdl.V[t-1] + mdl.dV[t])
    m.bal = pyo.Constraint(m.T, rule=_bal)

    # -------- связь Q–ΔV --------------
    m.qdef = pyo.Constraint(
        m.T, rule=lambda mdl, t: mdl.Q[t] == Q_byt[t] - mdl.dV[t]*1e9/dt
    )

    # -------- Z_up_prev ---------------
    m.zprev = pyo.Constraint(
        m.T, rule=lambda mdl, t: mdl.Z_up_prev[t] ==
            (levels.nrl if t == 1 else mdl.Z_up[t-1])
    )

    # -------- мощность ----------------
    coef = 8.5/1000
    m.pow = pyo.Constraint(
        m.T, rule=lambda mdl, t:
            mdl.P[t] == coef * mdl.Q[t] *
                        (0.5*(mdl.Z_up_prev[t] + mdl.Z_up[t]) - mdl.Z_low[t])
    )
    m.gar = pyo.Constraint(
        m.T, rule=lambda mdl, t: mdl.P[t] >= safety * P_gar[t]
    )

    # -------- дойти до УМО ------------
    m.hit_dead = pyo.Constraint(expr=m.V[t_dead] <= m.V_DEAD + 1e-4)

    # -------- годовой баланс ----------
    m.mass = pyo.Constraint(expr=sum(m.dV[t] for t in m.T) == 0)

    # -------- цель --------------------
    m.obj = pyo.Objective(expr=sum(m.P[t] for t in m.T), sense=pyo.maximize)

    # стартовые точки
    for t in m.T:
        m.V[t].value = V_nrl
        m.Q[t].value = Q_byt[t]
        m.Z_up_prev[t].value = levels.nrl

    if solver:
        opt = pyo.SolverFactory(solver)
        if opt is None:
            raise RuntimeError(f"Pyomo solver '{solver}' is not available")
        result = opt.solve(m)
        m.solutions.load_from(result)

    return m
