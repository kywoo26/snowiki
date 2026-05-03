from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class NormalizedRecord:
    id: str
    path: str
    source_type: str
    record_type: str
    recorded_at: str
    payload: dict[str, Any]
    raw_refs: list[dict[str, Any]]


__all__ = ["NormalizedRecord"]
