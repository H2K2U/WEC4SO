# wec/__init__.py
"""Пакет **WEC** (Water‑Energy Calculations).

Инициализационный модуль упрощает импорт «ключевых сущностей»
библиотеки для внешних пользователей:

--- from wec import WECAnalyzer, Geometry, StaticLevels, HydrologicalSeries ---

Экспортируемые объекты перечислены в ``__all__`` — это служит
*public API* пакета, ограничивая автодополнение и документацию теми
классами, которые нужны снаружи.
"""

from __future__ import annotations

from .facade.analyzer import WECAnalyzer
from .domain.geometry import Geometry
from .domain.static_levels import StaticLevels
from .domain.hydrological_series import HydrologicalSeries

__all__ = [
    "WECAnalyzer",  # фасад для расчётов и графиков
    "Geometry",      # геометрия гидроузла (кривые V‑Z, Q‑Z)
    "StaticLevels",  # НПУ, УМО, установленная мощность
    "HydrologicalSeries",  # Q_быт, N_гар по месяцам
]