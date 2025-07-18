# wec/domain/static_levels.py

from dataclasses import dataclass

@dataclass(slots=True)
class StaticLevels:
    """Fixed regulatory levels."""
    nrl: float  # НПУ - Normal Retaining Level (м)
    dead: float  # УМО - Dead volume level (м)
    installed_capacity: float  # МВт - Installed capacity (МВт)