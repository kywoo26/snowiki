from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from .scoring import HitScorer


@dataclass(frozen=True, slots=True)
class RuntimeSearchRequest:
    query: str
    candidate_limit: int
    recorded_after: datetime | None = None
    recorded_before: datetime | None = None
    exact_path_bias: bool = False
    kind_weights: Mapping[str, float] | None = None
    scoring_policy: HitScorer | None = None

    def __post_init__(self) -> None:
        if self.candidate_limit < 0:
            raise ValueError("candidate_limit must be non-negative")
        if self.kind_weights is not None:
            object.__setattr__(
                self,
                "kind_weights",
                MappingProxyType(dict(self.kind_weights)),
            )
