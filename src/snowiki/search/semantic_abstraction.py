from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .indexer import SearchDocument, SearchHit


class SemanticBackend(Protocol):
    enabled: bool

    def search(
        self, query: str, *, documents: Sequence[SearchDocument], limit: int = 10
    ) -> list[SearchHit]: ...


@dataclass(frozen=True)
class DisabledSemanticBackend:
    enabled: bool = False

    def search(
        self, query: str, *, documents: Sequence[SearchDocument], limit: int = 10
    ) -> list[SearchHit]:
        del query, documents, limit
        return []
