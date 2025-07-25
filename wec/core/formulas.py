# wec/core/formulas.py
"""Формулы для гидравлических и энергетических расчётов, используемые
во всём проекте WEC.

Модуль содержит набор компактных функций‑помощников, которые
преобразуют гидрологические или водохранилищные параметры
(расход, объём) в ключевые отметки и мощности, необходимые для
алгоритмов оптимизации.  Все функции чистые: они не изменяют
объект :class:`~wec.domain.geometry.Geometry`, а только читают его
данные.
"""

from __future__ import annotations

from .interpolation import Interpolator, default_interp
from ..domain.geometry import Geometry

# ---------------------------------------------------------------------------
# Базовые функции‑помощники
# ---------------------------------------------------------------------------


def compute_lowwater_mark(q: float, geom: Geometry, interp: Interpolator = default_interp) -> float:
    """Вычислить *уровень нижнего бьефа* **Zₙб** (м).

    Значение получается линейной или сплайн‑интерполяцией по расходной
    Q–Z кривой, хранящейся в объекте :class:`Geometry`.

    Параметры
    ----------
    q : float
        Сброс через турбину или общий расход в нижний бьеф (м³/с).
    geom : Geometry
        Геометрия гидроузла с набором кривых.
    interp : Interpolator, optional
        Объект интерполятора; по умолчанию берётся глобальный
        ``default_interp``.

    Возвращает
    ----------
    float
        Отметка нижнего бьефа Zₙб, м БС.
    """
    # Интерполируем точку расходной кривой (Q → Zₙб)
    return interp(q, geom.lowwater_inflows, geom.lowwater_marks)


def compute_headwater_mark(volume: float, geom: Geometry, interp: Interpolator = default_interp) -> float:
    """Вычислить *уровень верхнего бьефа* **Zᵥб** (м) для заданного объёма.

    Используется кривая наполнение‑отметка (V–Z) из :class:`Geometry`.
    """
    # Интерполируем точку кривой наполнение‑отметка (V → Zᵥб)
    return interp(volume, geom.average_volumes, geom.headwater_marks)


def compute_domestic_capacity(q: float, h: float) -> float:
    """Рассчитать *бытовую* мощность (МВт) по расходу **Q** и напору **H**.

    В российской практике гидроэнергетики часто применяют эмпирическую
    формулу

        ``N = 8.5 × Q × H / 1000``

    где
        * ``Q`` — расход через турбину (м³/с),
        * ``H`` — нетто‑напор (м),
        * множитель **8.5** агрегирует плотность воды, ускорение свободного
          падения и усреднённый КПД агрегатов,
        * деление на 1000 переводит кВт в МВт.
    """
    return 8.5 * q * h / 1000.0