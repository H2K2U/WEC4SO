# wec/optimizers/greedy.py
"""Простой «учебный» жадный алгоритм годового управления ΔV.

Алгоритм повторяет методику из классических пособий по гидроэнергетике:

1. **Сработка (DISCHARGE):**
   * Для каждого *discharge*-месяца пошагово увеличивается расход
     водохранилища (ΔV>0 ⇒ Q_ГЭС↑), пока расчётная мощность
     N_ГЭС не превысит 105% от гарантированной N_гар.
   * Полученные объёмы срабатываемой воды сохраняются в списке
     ``disc_vol`` (положительные значения).

2. **Наполнение (FILL):**
   * Суммарный объём сработки равномерно распределяется по *fill*-месяцам
     (``_initial_fill``).  Затем вызывается балансировка ``_balance_fill``:
     она переносит по 0.01 км³ от «богатых» месяцев к «бедным», пока во
     **всех** месяцах наполнение не даст N_ГЭС ≥ 105% N_гар.

3. Итоговый вектор ΔV строится со знаком:
   * DISCHARGE → ΔV<0 (водоём опустошается),
   * FILL       → ΔV>0 (водоём наполняется).

Алгоритм **гарантирует** замыкание годового цикла (∑ΔV≈0) при
корректно подобранных объёмах.  Проверка вынесена в ``assert``.
"""

from __future__ import annotations

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
    """Жадный (Greedy) оптимизатор годовых ΔV."""

    # ------------------------------------------------------------------
    # Главный публичный метод интерфейса AbstractOptimizer
    # ------------------------------------------------------------------

    def compute_dV(self, geom, levels, series, modes) -> List[float]:
        # --- разделяем индексы месяцев по режимам ---
        fill_idx = [i for i, m in enumerate(modes) if m is OperationMode.FILL]
        disc_idx = [i for i, m in enumerate(modes) if m is OperationMode.DISCHARGE]

        # 1. Определяем объёмы сработки (положительные числа; км³)
        disc_vol = self._calc_discharge(geom, levels, series, disc_idx)

        # 2. Раскладываем сработку по fill‑месяцам и балансируем
        fill_vol = self._balance_fill(
            geom,
            levels,
            series,
            self._initial_fill(sum(disc_vol), fill_idx),
            fill_idx,
            disc_vol,
        )

        # 3. Собираем итоговый «знаковый» список ΔV
        dv: list[float] = []
        di = fi = 0
        for m in modes:
            if m is OperationMode.DISCHARGE:
                dv.append(-disc_vol[di])  # отрицательно: объём уменьшается
                di += 1
            else:
                dv.append(+fill_vol[fi])  # положительно: объём растёт
                fi += 1

        # Контроль замыкания годового цикла: сумма ΔV ≈ 0
        assert abs(sum(dv)) < 1e-6, "Greedy plan does not return to NPU"
        return dv

    # ------------------------------------------------------------------
    # Внутренние методы («кухня» алгоритма)
    # ------------------------------------------------------------------

    def _calc_discharge(self, geom, levels, series, d_idx):
        """Подбор объёма сработки для каждого DISCHARGE‑месяца."""
        vols = [0.0] * len(d_idx)
        for k, idx in enumerate(d_idx):
            q_byt = series.domestic_inflows[idx]
            n_gar = series.guaranteed_capacity[idx]
            dV = 0.0  # начинаем с нулевой сработки
            while True:
                # учёт знака: ΔV (+) → отбор, но расход Q_ГЭС ↑
                q_ges = q_byt + dV * 1e9 / SECONDS_PER_MONTH
                z_low = compute_lowwater_mark(q_ges, geom)
                n_ges = min(
                    compute_domestic_capacity(q_ges, levels.nrl - z_low),
                    levels.installed_capacity,
                )
                if n_ges >= 1.05 * n_gar:
                    break  # достигли цели 105 % N_гар
                dV += 0.01  # шаг объёма, км³
            vols[k] = dV
        return vols

    @staticmethod
    def _initial_fill(total_discharge, fill_idx):
        """Первичное равномерное распределение сработанного объёма."""
        return [] if not fill_idx else [total_discharge / len(fill_idx)] * len(fill_idx)

    def _balance_fill(self, geom, levels, series, vols, f_idx, disc_vols):
        """Балансировка fill‑месяцев: перенос 0.01 км³ от «богатых» к «бедным»."""
        if not f_idx:
            return []
        v = vols.copy()
        caps = self._recompute_caps(geom, levels, series, v, f_idx)
        for i, idx in enumerate(f_idx):
            n_gar = series.guaranteed_capacity[idx]
            while caps[i] < 1.05 * n_gar and v[i] >= 0.01:
                j = int(np.argmax(caps))  # месяц с максимальным запасом мощности
                v[j] += 0.01
                v[i] -= 0.01
                caps[i] = self._cap_single(geom, levels, series, v[i], idx)
                caps[j] = self._cap_single(geom, levels, series, v[j], f_idx[j])
        return v

    # ------------------------------------------------------------------
    # Helper‑функции пересчёта мощностей
    # ------------------------------------------------------------------

    def _recompute_caps(self, geom, levels, series, vols, idx_list):
        caps = []
        vol = levels.nrl  # стартуем с НПУ
        for dV, idx in zip(vols, idx_list):
            q = series.domestic_inflows[idx] - dV * 1e9 / SECONDS_PER_MONTH
            vol_end = vol + dV
            avg_h = 0.5 * (
                compute_headwater_mark(vol, geom)
                + compute_headwater_mark(vol_end, geom)
            )
            z_low = compute_lowwater_mark(q, geom)
            caps.append(compute_domestic_capacity(q, avg_h - z_low))
            vol = vol_end  # переход к следующему месяцу
        return caps

    def _cap_single(self, geom, levels, series, dV, idx):
        """Мощность ГЭС в **одном** fill‑месяце при заданном dV."""
        q = series.domestic_inflows[idx] - dV * 1e9 / SECONDS_PER_MONTH
        avg_h = compute_headwater_mark(levels.nrl + dV, geom)
        return compute_domestic_capacity(
            q, avg_h - compute_lowwater_mark(q, geom)
        )
