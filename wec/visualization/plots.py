# wec/visualization/plots.py

import matplotlib.pyplot as plt
import pandas as pd
from ..domain.hydrological_series import HydrologicalSeries
from ..domain.static_levels import StaticLevels

def plot_domestic_inflow(series: HydrologicalSeries) -> None:
    plt.bar(series.months, series.domestic_inflows)
    plt.title("Бытовая приточность по месяцам")
    plt.xlabel("Месяц"); plt.ylabel("Q, м³/с"); plt.grid(True); plt.show()

def plot_guaranteed_capacity(series: HydrologicalSeries) -> None:
    plt.bar(series.months, series.guaranteed_capacity)
    plt.title("Гарантированная мощность по месяцам")
    plt.xlabel("Месяц"); plt.ylabel("Nгар, МВт"); plt.grid(True); plt.show()

def plot_reservoir_levels(df: pd.DataFrame, levels: StaticLevels) -> None:
    x = range(len(df) + 1)
    y = list(df["Z_вб_нач, м"]) + [df["Z_вб_кон, м"].iloc[-1]]
    months = list(df["Месяц"]) + [df["Месяц"].iloc[0]]
    plt.plot(x, y)
    plt.xticks(x, months)
    plt.axhline(levels.nrl, ls="--", color="red", label="НПУ")
    plt.axhline(levels.dead, ls="--", color="green", label="УМО")
    plt.title("График сработки и наполнения водохранилища\nна годовом интервале с шагом в один месяц")
    plt.xlabel("Месяц"); plt.ylabel("Zвб, м")
    plt.grid(True); plt.legend(); plt.show()
