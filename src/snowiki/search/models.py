from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

SEARCH_DOCUMENT_FORMAT_VERSION = "1"
LEXICAL_INDEX_FORMAT_VERSION = "1"

type SearchScalar = None | bool | int | float | str
type SearchValue = SearchScalar | list[SearchValue] | dict[str, SearchValue]


@dataclass(frozen=True)
class SearchDocument:
    """Searchable document returned by runtime retrieval indexes.

    `content` stores primary body text only. Search indexes should use
    `searchable_texts()` to collect the promoted searchable fields.
    """

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

    def searchable_texts(self) -> tuple[str, ...]:
        """Return non-empty searchable fields without including metadata.

        `content` is primary body text only, so title/path/summary/aliases stay
        explicit here instead of being flattened into the body field.
        """

        fields = (
            self.title,
            self.path,
            self.summary,
            self.content,
            " ".join(self.aliases),
        )
        return tuple(field for field in fields if field and field.strip())


@dataclass(frozen=True)
class SearchHit:
    """Scored search hit returned by runtime retrieval indexes."""

    document: SearchDocument
    score: float
    matched_terms: tuple[str, ...]
