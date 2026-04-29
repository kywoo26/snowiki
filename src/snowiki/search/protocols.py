from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from .models import SearchHit
from .registry import SearchTokenizer


class RuntimeSearchIndex(Protocol):
    """Primary runtime search interface used by query and recall policies."""

    @property
    def size(self) -> int: ...

    @property
    def tokenizer(self) -> SearchTokenizer: ...

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        kind_weights: Mapping[str, float] | None = None,
        recorded_after: datetime | None = None,
        recorded_before: datetime | None = None,
        exact_path_bias: bool = False,
    ) -> list[SearchHit]: ...
