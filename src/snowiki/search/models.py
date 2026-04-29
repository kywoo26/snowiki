from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

type SearchScalar = None | bool | int | float | str
type SearchValue = SearchScalar | list[SearchValue] | dict[str, SearchValue]


@dataclass(frozen=True)
class SearchDocument:
    """Searchable document returned by runtime retrieval indexes."""

    id: str
    path: str
    kind: str
    title: str
    content: str
    summary: str = ""
    aliases: tuple[str, ...] = ()
    recorded_at: datetime | None = None
    source_type: str = ""
    metadata: dict[str, SearchValue] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchHit:
    """Scored search hit returned by runtime retrieval indexes."""

    document: SearchDocument
    score: float
    matched_terms: tuple[str, ...]
