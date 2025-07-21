# wec/domain/geometry.py
"""Описание геометрии водохранилища и руслового участка.

Модель собирает *минимально* необходимый набор кривых, которые
используются всеми расчётными модулями:

* **headwater_marks** – отметки верхнего бьефа *Zᵥб* (м) при разных
  объёмах; используется совместно с ``average_volumes`` для обратного
  перехода V ↔ Z.
* **average_volumes** – усреднённые объёмы водохранилища *Vср* (км³)
  при тех же уровнях ``headwater_marks``.  Пары *(Z, V)* образуют кривую
  наполнение‑отметка.
* **lowwater_marks** – отметки нижнего бьефа *Zₙб* (м) при разных
  расходах.
* **lowwater_inflows** – расходы *Qₙб* (м³/с), соответствующие
  ``lowwater_marks``.  Пары *(Q, Z)* образуют расходную кривую.

Предполагается, что массивы:
* ``headwater_marks`` и ``average_volumes`` упорядочены **по возрастанию
  отметки** (или, что то же, по возрастанию объёма);
* ``lowwater_inflows`` и ``lowwater_marks`` упорядочены **по возрастанию
  расхода**.

Это упрощает интерполяцию с помощью ``numpy.interp`` / ``scipy``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class Geometry:
    """Контейнер геометрических (гидравлических) кривых гидроузла."""

    # --- Верхний бьеф (водохранилище) ---
    headwater_marks: List[float]      # отметка Zᵥб, м БС
    average_volumes: List[float]      # объём Vср, км³

    # --- Нижний бьеф (русло) ---
    lowwater_marks: List[float]       # отметка Zₙб, м БС
    lowwater_inflows: List[float]     # расход Qₙб, м³/с
