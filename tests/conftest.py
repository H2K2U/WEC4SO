import importlib
import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

Geometry = importlib.import_module('wec.domain.geometry').Geometry
StaticLevels = importlib.import_module('wec.domain.static_levels').StaticLevels
HydrologicalSeries = importlib.import_module('wec.domain.hydrological_series').HydrologicalSeries

@pytest.fixture
def geometry():
    return Geometry(
        headwater_marks=[87, 89, 91, 93, 95, 97, 99, 101, 103],
        average_volumes=[0.1, 0.4, 0.9, 2.3, 4.6, 8.8, 14.6, 21, 29.3],
        lowwater_marks=[81, 83, 85, 87, 89, 91],
        lowwater_inflows=[100, 460, 1200, 2250, 3800, 5100],
    )

@pytest.fixture
def static_levels():
    return StaticLevels(nrl=102, dead=100, installed_capacity=500)

@pytest.fixture
def hydro_series():
    return HydrologicalSeries(
        months=list(range(1, 13)),
        domestic_inflows=[540, 450, 740, 2850, 3500, 1100, 750, 630, 450, 465, 560, 410],
        guaranteed_capacity=[130, 130, 135, 220, 200, 190, 50, 50, 50, 140, 140, 140],
    )
