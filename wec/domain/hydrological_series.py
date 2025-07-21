# wec/domain/hydrological_series.py
"""Ежемесячные гидрологические и энергетические ряды для расчёта режима.

Содержит три синхронизированных списка одной длины (обычно 12):
* **months** – номера месяцев (1…12).  Можно хранить в любом порядке;
  *MonthSelector* в дальнейшем может «повернуть» список.
* **domestic_inflows** – *бытовые притоки* Q_быт, м³/с (средние за месяц).
* **guaranteed_capacity** – гарантированная мощность N_гар, МВт, которую
  ГЭС обязана выдавать в соответствующий месяц.

Класс выступает простым контейнером с минимальной проверкой длины
списков в ``__post_init__``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class HydrologicalSeries:
    """Контейнер ежемесячных гидрологических данных."""

    months: List[int]                # календарные месяцы 1–12
    domestic_inflows: List[float]    # Q_быт (м³/с)
    guaranteed_capacity: List[float] # N_гар (МВт)

    # Лёгкая санитарная проверка на согласованность длин
    def __post_init__(self) -> None:
        if not (
            len(self.months)
            == len(self.domestic_inflows)
            == len(self.guaranteed_capacity)
        ):
            raise ValueError(
                "All hydrological time‑series must have equal length."
            )
