from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from .indexer import SearchHit, SearchTokenizer


class RuntimeSearchIndex(Protocol):
    """Search interface shared by legacy and BM25 runtime indexes."""

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
