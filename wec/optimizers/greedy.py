# wec/optimizers/greedy.py
from typing import List
import numpy as np

from . import AbstractOptimizer
from ..core.month_selector import OperationMode
from ..core.formulas import (
    compute_headwater_mark,
    compute_lowwater_mark,
    compute_domestic_capacity,
)
from ..constants import SECONDS_PER_MONTH


class GreedyOptimizer(AbstractOptimizer):
    """
    «Учебный» алгоритм из пособия:
    • на месяцы‑сработки подбираем расход, пока N_ГЭС ≥ 1.05·N_гар;
    • суммарный объём сработки равномерно раскладываем по fill‑месяцам
      (затем балансируем, чтобы и там N ≥ 1.05·N_гар);
    • итоговый годовой баланс ∑ ΔV = 0.
    ΔV возвращаем со знаком:
        DISCHARGE →  ΔV < 0   (объём уменьшается)
        FILL       →  ΔV > 0   (объём растёт)
    """

    # --------------------------------------------------------------
    def compute_dV(self, geom, levels, series, modes) -> List[float]:
        fill_idx  = [i for i, m in enumerate(modes) if m is OperationMode.FILL]
        disc_idx  = [i for i, m in enumerate(modes) if m is OperationMode.DISCHARGE]

        # 1. подбираем объёмы сработки (положительные числа)
        disc_vol = self._calc_discharge(geom, levels, series, disc_idx)

        # 2. равномерно кладём их на fill‑месяцы, затем балансируем
        fill_vol = self._balance_fill(
            geom, levels, series,
            self._initial_fill(sum(disc_vol), fill_idx),
            fill_idx, disc_vol
        )

        # 3. собираем итоговый знаковый список ΔV
        dv: list[float] = []
        di = fi = 0
        for m in modes:
            if m is OperationMode.DISCHARGE:
                dv.append(-disc_vol[di])  # сработка ↓   (минус)
                di += 1
            else:
                dv.append(+fill_vol[fi])  # наполнение ↑ (плюс)
                fi += 1
        # контроль: год должен замкнуться
        assert abs(sum(dv)) < 1e-6, "Greedy plan does not return to NPU"
        return dv

    # --------------------------------------------------------------
    # ↓ дальше — почти прежние внутренние функции,
    #   изменён только знак при расчёте расхода
    def _calc_discharge(self, geom, levels, series, d_idx):
        vols = [0.0]*len(d_idx)
        for k, idx in enumerate(d_idx):
            q_byt  = series.domestic_inflows[idx]
            n_gar  = series.guaranteed_capacity[idx]
            dV = 0.0
            while True:
                q_ges = q_byt + dV*1e9/SECONDS_PER_MONTH
                z_low = compute_lowwater_mark(q_ges, geom)
                n_ges = min(
                    compute_domestic_capacity(q_ges, levels.nrl - z_low),
                    levels.installed_capacity,
                )
                if n_ges >= 1.05*n_gar:
                    break
                dV += 0.01  # км³
            vols[k] = dV
        return vols

    @staticmethod
    def _initial_fill(total_discharge, fill_idx):
        return [] if not fill_idx else [total_discharge/len(fill_idx)]*len(fill_idx)

    def _balance_fill(self, geom, levels, series, vols, f_idx, disc_vols):
        if not f_idx:
            return []
        v = vols.copy()
        caps = self._recompute_caps(geom, levels, series, v, f_idx)
        for i, idx in enumerate(f_idx):
            n_gar = series.guaranteed_capacity[idx]
            while caps[i] < 1.05*n_gar and v[i] >= 0.01:
                j = int(np.argmax(caps))
                v[j] += 0.01; v[i] -= 0.01
                caps[i] = self._cap_single(geom, levels, series, v[i], idx)
                caps[j] = self._cap_single(geom, levels, series, v[j], f_idx[j])
        return v

    # -- helpers ----------------------------------------------------
    def _recompute_caps(self, geom, levels, series, vols, idx_list):
        caps=[]; vol=levels.nrl
        for dV, idx in zip(vols, idx_list):
            q  = series.domestic_inflows[idx] - dV*1e9/SECONDS_PER_MONTH
            vol_end = vol + dV
            avg_h = 0.5*(compute_headwater_mark(vol, geom)
                         + compute_headwater_mark(vol_end, geom))
            z_low = compute_lowwater_mark(q, geom)
            caps.append(compute_domestic_capacity(q, avg_h - z_low))
            vol = vol_end
        return caps

    def _cap_single(self, geom, levels, series, dV, idx):
        q = series.domestic_inflows[idx] - dV*1e9/SECONDS_PER_MONTH
        avg_h = compute_headwater_mark(levels.nrl + dV, geom)
        return compute_domestic_capacity(q, avg_h - compute_lowwater_mark(q, geom))
