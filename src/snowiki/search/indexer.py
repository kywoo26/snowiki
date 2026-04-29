from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime

from snowiki.storage.zones import ensure_utc_datetime

from .models import SearchDocument, SearchHit, SearchValue
from .registry import SearchTokenizer, default
from .registry import create as create_tokenizer

FIELD_BOOSTS = {
    "title": 3.0,
    "path": 2.5,
    "summary": 1.75,
    "content": 1.0,
    "aliases": 2.0,
}


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return " ".join(_stringify(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _parse_recorded_at(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime | str):
        return ensure_utc_datetime(value)
    return None


class InvertedIndex:
    """In-memory inverted index for lexical and blended search."""

    def __init__(
        self,
        documents: Iterable[SearchDocument] = (),
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> None:
        self.documents: dict[str, SearchDocument] = {}
        self._postings: dict[str, dict[str, float]] = defaultdict(dict)
        self._field_tokens: dict[str, dict[str, tuple[str, ...]]] = {}
        self._normalized_haystacks: dict[str, tuple[str, ...]] = {}
        self._normalized_paths: dict[str, str] = {}
        self._tokenizer: SearchTokenizer
        self._tokenizer = tokenizer or create_tokenizer(default().name)
        for document in documents:
            self.add_document(document)

    @property
    def tokenizer(self) -> SearchTokenizer:
        return self._tokenizer

    @property
    def size(self) -> int:
        return len(self.documents)

    def add_document(self, document: SearchDocument) -> None:
        if document.id in self.documents:
            for postings in self._postings.values():
                postings.pop(document.id, None)

        self.documents[document.id] = document
        field_tokens = {
            "title": self._tokenizer.tokenize(document.title),
            "path": self._tokenizer.tokenize(document.path),
            "summary": self._tokenizer.tokenize(document.summary),
            "content": self._tokenizer.tokenize(document.content),
            "aliases": self._tokenizer.tokenize(" ".join(document.aliases)),
        }
        self._field_tokens[document.id] = field_tokens
        normalized_path = self._tokenizer.normalize(document.path)
        self._normalized_paths[document.id] = normalized_path
        self._normalized_haystacks[document.id] = tuple(
            normalized
            for normalized in (
                self._tokenizer.normalize(document.title),
                normalized_path,
                self._tokenizer.normalize(document.summary),
                self._tokenizer.normalize(document.content),
            )
            if normalized
        )

        for field_name, tokens in field_tokens.items():
            counts = Counter(tokens)
            boost = FIELD_BOOSTS[field_name]
            for token, count in counts.items():
                self._postings[token][document.id] = self._postings[token].get(
                    document.id, 0.0
                ) + (count * boost)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        kind_weights: Mapping[str, float] | None = None,
        recorded_after: datetime | None = None,
        recorded_before: datetime | None = None,
        exact_path_bias: bool = False,
    ) -> list[SearchHit]:
        query_tokens = self._tokenizer.tokenize(query)
        if not query_tokens:
            return []

        scores: defaultdict[str, float] = defaultdict(float)
        matches: dict[str, set[str]] = defaultdict(set)
        document_count = max(self.size, 1)

        for token in query_tokens:
            postings = self._postings.get(token)
            if not postings:
                continue
            document_frequency = len(postings)
            inverse_document_frequency = (
                math.log((1 + document_count) / (1 + document_frequency)) + 1.0
            )
            for document_id, weighted_frequency in postings.items():
                scores[document_id] += weighted_frequency * inverse_document_frequency
                matches[document_id].add(token)

        normalized_query = self._tokenizer.normalize(query)
        hits: list[SearchHit] = []
        for document_id, score in scores.items():
            document = self.documents[document_id]
            if recorded_after is not None and (
                document.recorded_at is None or document.recorded_at < recorded_after
            ):
                continue
            if recorded_before is not None and (
                document.recorded_at is None or document.recorded_at > recorded_before
            ):
                continue

            matched_terms = matches[document_id]
            coverage = len(matched_terms) / len(query_tokens)
            score += coverage * 4.0

            if any(
                normalized_query in haystack
                for haystack in self._normalized_haystacks[document_id]
            ):
                score += 3.0

            normalized_path = self._normalized_paths[document_id]
            if exact_path_bias and any(
                token in normalized_path for token in query_tokens
            ):
                score += 2.0
            if normalized_query in normalized_path:
                score += 2.5

            if kind_weights is not None:
                score *= kind_weights.get(document.kind, 1.0)

            recency = (
                document.recorded_at.timestamp()
                if document.recorded_at is not None
                else 0.0
            )
            hits.append(
                SearchHit(
                    document=document,
                    score=score + (recency / 10_000_000_000.0),
                    matched_terms=tuple(sorted(matched_terms)),
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.document.path, hit.document.id))
        return hits[:limit]


def _coerce_aliases(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple | set):
        return tuple(_stringify(item) for item in value if _stringify(item))
    rendered = _stringify(value)
    return (rendered,) if rendered else ()


def document_from_mapping(
    payload: Mapping[str, SearchValue],
    *,
    kind: str,
    source_type: str,
    id_key: str = "id",
    path_key: str = "path",
    title_key: str = "title",
    summary_key: str = "summary",
    content_keys: Iterable[str] = ("content", "text", "body"),
    alias_keys: Iterable[str] = ("aliases", "tags", "identity_keys"),
    recorded_at_keys: Iterable[str] = (
        "recorded_at",
        "updated_at",
        "created_at",
        "timestamp",
        "started_at",
    ),
) -> SearchDocument:
    """Build a searchable document from a generic mapping payload."""
    title = _stringify(
        payload.get(title_key)
        or payload.get(id_key)
        or payload.get(path_key)
        or "untitled"
    )
    path = _stringify(payload.get(path_key) or payload.get(id_key) or title)
    summary = _stringify(payload.get(summary_key))
    content_parts = [title, path, summary]
    for key in content_keys:
        content_parts.append(_stringify(payload.get(key)))
    content_parts.append(_stringify(payload))

    recorded_at = None
    for key in recorded_at_keys:
        recorded_at = _parse_recorded_at(payload.get(key))
        if recorded_at is not None:
            break

    alias_values: list[str] = []
    for key in alias_keys:
        alias_values.extend(_coerce_aliases(payload.get(key)))

    return SearchDocument(
        id=_stringify(payload.get(id_key) or path),
        path=path,
        kind=kind,
        title=title,
        content="\n".join(part for part in content_parts if part),
        summary=summary,
        aliases=tuple(dict.fromkeys(alias_values)),
        recorded_at=recorded_at,
        source_type=source_type,
        metadata=dict(payload),
    )


def build_blended_index(
    *document_groups: Iterable[SearchDocument],
    tokenizer: SearchTokenizer | None = None,
) -> InvertedIndex:
    """Build a single search index from multiple document groups."""
    documents: list[SearchDocument] = []
    for group in document_groups:
        documents.extend(group)
    return InvertedIndex(documents, tokenizer=tokenizer)
