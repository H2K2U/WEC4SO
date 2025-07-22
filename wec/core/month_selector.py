# wec/core/month_selector.py
"""Определение режимов работы ГЭС в каждый месяц.

Модуль выделяет два типа месячных режимов:
* **сработка** (DISCHARGE) — период, когда бытовой (естественный) расход
  не позволяет обеспечить гарантированную мощность, поэтому приходится
  расходовать запасы водохранилища;
* **наполнение** (FILL) — период, когда притока достаточно (или в избытке)
  и уровень можно/нужно поднимать.

Алгоритм выполняет два шага:
1. Для каждого месяца классифицирует режим исходя из сравнения
   *бытовой* мощности (рассчитанной по формуле 8.5*Q*H/1000 на уровне
   НПУ) с графиком **N_гар**.
2. Устраняет одиночные «ложные» месяцы наполнения, вклинившиеся между
   двумя месяцами сработки (частый артефакт кривых).
3. Поворачивает год так, чтобы первым шёл первый месяц сработки,
   начинающийся *после* сентября (индекс > 8). Это упрощает логику
   последующих алгоритмов, которым удобнее стартовать годовой цикл с
   началом осенне‑зимнего периода дефицита.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import List, Sequence, Tuple

from ..domain.hydrological_series import HydrologicalSeries
from ..domain.geometry import Geometry
from ..domain.static_levels import StaticLevels
from .interpolation import Interpolator, default_interp
from .formulas import compute_lowwater_mark, compute_domestic_capacity

logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Перечисление режимов работы ГЭС в месячном разрезе."""

    FILL = auto()       # «наполнение» водохранилища
    DISCHARGE = auto()  # «сработка» (расход запасённой воды)

    # Улучшенный вывод в лог/print
    def __str__(self) -> str:  # prettier string
        return "наполнение" if self is OperationMode.FILL else "сработка"


class MonthSelector:
    """Класс‑утилита для формирования годовой последовательности месяцев.

    На вход подаются гидрологические ряды, геометрия гидроузла и
    статические уровни (НПУ, УМО и др.).  На выходе:
    1. Список режимов (*OperationMode*) для каждого календарного месяца.
    2. *Повернутый* (rotated) гидрологический ряд, где год начинается с
       первого месяца сработки после сентября (т.е. ближе к октябрю), что
       упрощает дальнейшие годовые расчёты.
    """

    def __init__(
        self,
        series: HydrologicalSeries,
        geom: Geometry,
        levels: StaticLevels,
        interp: Interpolator = default_interp,
    ):
        self._s = series
        self._geom = geom
        self._levels = levels
        self._interp = interp

    # ------------------------------------------------------------------
    # Шаг 1: классификация месяцев без поворота
    # ------------------------------------------------------------------

    def calc_modes(self) -> List[OperationMode]:
        """Возвращает список режимов для текущего календарного порядка.

        Месяц считается *сработкой*, если бытовая мощность **N_быт**
        (рассчитанная при уровне НПУ) меньше гарантированной **N_гар**.
        Независимо от того, насколько больше **N_гар**, запас ≥ 1 МВт
        считается достаточным.
        """
        modes: List[OperationMode] = []
        nrl_level = self._levels.nrl  # нормальный подпорный уровень

        # --- первичная классификация ---
        for q_byt, n_gar in zip(self._s.domestic_inflows, self._s.guaranteed_capacity):
            # Отметка нижнего бьефа при бытовом расходе Q_быт
            z_low = compute_lowwater_mark(q_byt, self._geom, self._interp)
            head = nrl_level - z_low  # предполагаем, что водоём полон (НПУ)
            n_byt = compute_domestic_capacity(q_byt, head)

            mode = OperationMode.DISCHARGE if n_byt < n_gar else OperationMode.FILL
            modes.append(mode)

        # --- фильтрация одиночных «ложных» наполнений ---
        for i in range(1, len(modes) - 1):
            if (
                modes[i - 1] is OperationMode.DISCHARGE
                and modes[i]     is OperationMode.FILL
                and modes[i + 1] is OperationMode.DISCHARGE
            ):
                # Считаем промежуточный месяц частью периода сработки
                modes[i] = OperationMode.DISCHARGE
          # --- обработка циклического края года (D‑F‑D через границу) ---

        if (
            modes[-1] is OperationMode.DISCHARGE
            and modes[0] is OperationMode.FILL
            and modes[1] is OperationMode.DISCHARGE
        ):
            modes[0] = OperationMode.DISCHARGE

        if (
            modes[-2] is OperationMode.DISCHARGE
            and modes[-1] is OperationMode.FILL
            and modes[0] is OperationMode.DISCHARGE
        ):
            modes[-1] = OperationMode.DISCHARGE
        return modes

    # ------------------------------------------------------------------
    # Шаг 2: поворот годовой последовательности месяцев
    # ------------------------------------------------------------------

    def rotated(self) -> Tuple[HydrologicalSeries, List[OperationMode]]:
        """Возвращает (*повёрнутый ряд*, *список режимов*).

        Ищем первый месяц сработки с индексом > 8 (т.е. после сентября) и
        считаем его началом года.  Если такой месяц не найден, оставляем
        исходный порядок, но выводим предупреждение в лог.
        """
        modes = self.calc_modes()
        try:
            # Первый DISCHARGE‑месяц после сентября (индекс > 8)
            start_idx = next(
                i for i, m in enumerate(modes) if m is OperationMode.DISCHARGE and i > 8
            )
        except StopIteration:
            logger.warning(
                "No discharge month found after September; keeping original order."
            )
            return self._s, modes  # ничего не поворачиваем

        # Локальная вспомогательная функция для поворота списка/кортежа
        def _rot(lst: Sequence):
            return list(lst[start_idx:]) + list(lst[:start_idx])

        # Собираем новый объект HydrologicalSeries с повернутыми массивами
        rotated_series = HydrologicalSeries(
            months=_rot(self._s.months),
            domestic_inflows=_rot(self._s.domestic_inflows),
            guaranteed_capacity=_rot(self._s.guaranteed_capacity),
        )
        rotated_modes = _rot(modes)
        return rotated_series, rotated_modes
