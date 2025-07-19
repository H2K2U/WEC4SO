"""Minimal pandas stub for testing without external dependency."""

from typing import List, Dict, Any

class DataFrame:
    def __init__(self, records: List[Dict[str, Any]]):
        self._records = list(records)

    @classmethod
    def from_records(cls, records: List[Dict[str, Any]]):
        return cls(records)

    def __getitem__(self, key: str) -> List[Any]:
        return [r[key] for r in self._records]

    def __repr__(self) -> str:
        return f"DataFrame({self._records!r})"

def set_option(*args, **kwargs):
    pass
