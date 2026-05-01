from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class SearchIntentPolicy:
    name: str
    candidate_multiplier: int
    exact_path_bias: bool
    kind_weights: Mapping[str, float]
    use_kind_blending: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "kind_weights",
            MappingProxyType(dict(self.kind_weights)),
        )

    def candidate_limit(self, final_limit: int) -> int:
        if final_limit <= 0:
            return 0
        return max(final_limit, final_limit * self.candidate_multiplier)


KNOWN_ITEM_POLICY = SearchIntentPolicy(
    name="known-item",
    candidate_multiplier=3,
    exact_path_bias=True,
    kind_weights={"session": 1.15, "page": 0.85},
    use_kind_blending=False,
)

TOPICAL_POLICY = SearchIntentPolicy(
    name="topical",
    candidate_multiplier=4,
    exact_path_bias=False,
    kind_weights={"session": 1.0, "page": 1.0},
    use_kind_blending=True,
)

TEMPORAL_POLICY = SearchIntentPolicy(
    name="temporal",
    candidate_multiplier=3,
    exact_path_bias=False,
    kind_weights={"session": 1.0, "page": 1.0},
    use_kind_blending=False,
)

DATE_POLICY = SearchIntentPolicy(
    name="date",
    candidate_multiplier=3,
    exact_path_bias=False,
    kind_weights={"session": 1.0, "page": 1.0},
    use_kind_blending=False,
)
