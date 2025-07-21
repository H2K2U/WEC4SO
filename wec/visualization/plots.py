# wec/visualization/plots.py
"""Мини‑обёртки над matplotlib для отображения ключевых графиков.

Функции строят *интерактивные* графики (``plt.show()``) и не возвращают
объекты Figure/Axes, чтобы оставить API как можно более простым.
При желании можно доработать, чтобы принимать объект ``ax`` или
возвращать фигуру для встраивания в отчёты.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from ..domain.hydrological_series import HydrologicalSeries
from ..domain.static_levels import StaticLevels

# ---------------------------------------------------------------------------
# 1) График бытовых притоков
# ---------------------------------------------------------------------------

def plot_domestic_inflow(series: HydrologicalSeries) -> None:
    """Гистограмма Q_быт по месяцам."""
    plt.bar(series.months, series.domestic_inflows)
    plt.title("Бытовая приточность по месяцам")
    plt.xlabel("Месяц")
    plt.ylabel("Q, м³/с")
    plt.grid(True)
    plt.show()

# ---------------------------------------------------------------------------
# 2) График гарантированной мощности
# ---------------------------------------------------------------------------

def plot_guaranteed_capacity(series: HydrologicalSeries) -> None:
    """Гистограмма N_гар по месяцам."""
    plt.bar(series.months, series.guaranteed_capacity)
    plt.title("Гарантированная мощность по месяцам")
    plt.xlabel("Месяц")
    plt.ylabel("N_гар, МВт")
    plt.grid(True)
    plt.show()

# ---------------------------------------------------------------------------
# 3) График уровней водохранилища
# ---------------------------------------------------------------------------

def plot_reservoir_levels(df: pd.DataFrame, levels: StaticLevels) -> None:
    """Линия уровня верхнего бьефа за год + отметки НПУ/УМО."""
    x = range(len(df) + 1)
    y = list(df["Z_вб_нач, м"]) + [df["Z_вб_кон, м"].iloc[-1]]
    months = list(df["Месяц"]) + [df["Месяц"].iloc[0]]

    plt.plot(x, y, marker="o")
    plt.xticks(x, months)

    # Добавляем горизонтальные линии НПУ и УМО
    plt.axhline(levels.nrl, ls="--", color="red", label="НПУ")
    plt.axhline(levels.dead, ls="--", color="green", label="УМО")

    plt.title(
        "График сработки/наполнения водохранилища\n"
        "на годовом интервале (шаг = 1 месяц)"
    )
    plt.xlabel("Месяц")
    plt.ylabel("Z_вб, м")
    plt.grid(True)
    plt.legend()
    plt.show()
