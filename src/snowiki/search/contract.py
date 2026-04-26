from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Literal, Protocol, TypedDict, cast

from snowiki.storage.zones import ensure_utc_datetime

from .indexer import SearchHit
from .protocols import RuntimeSearchIndex

RecallStrategy = Literal["date", "temporal", "known_item", "topic"]
RecallMode = Literal["auto", "date", "temporal", "known_item", "topic"]

TEMPORAL_KEYWORDS: tuple[str, ...] = (
    "yesterday",
    "today",
    "last week",
    "this week",
    "어제",
    "오늘",
    "지난주",
    "이번주",
)


class NormalizedLexicalHit(TypedDict):
    """Canonical lexical parity fields shared across runtime surfaces."""

    kind: str
    matched_terms: list[str]
    path: str
    score: float
    title: str


class NormalizedRecallParityResult(TypedDict):
    """Canonical authoritative recall parity payload."""

    hits: list[NormalizedLexicalHit]
    strategy: RecallStrategy


class KnownItemLookupFn(Protocol):
    """Callable protocol for known-item lexical recall."""

    def __call__(
        self, index: RuntimeSearchIndex, query: str, *, limit: int
    ) -> list[SearchHit]: ...


class TopicalRecallFn(Protocol):
    """Callable protocol for topical lexical recall."""

    def __call__(
        self, index: RuntimeSearchIndex, query: str, *, limit: int
    ) -> list[SearchHit]: ...


class TemporalRecallFn(Protocol):
    """Callable protocol for temporal lexical recall."""

    def __call__(
        self,
        index: RuntimeSearchIndex,
        query: str,
        *,
        limit: int,
        reference_time: datetime | None = None,
    ) -> list[SearchHit]: ...


def iso_date_window(text: str) -> tuple[datetime, datetime] | None:
    """Return an inclusive calendar-day recall window for an ISO date string."""
    try:
        start = ensure_utc_datetime(datetime.fromisoformat(text))
    except ValueError:
        return None
    end = start + timedelta(days=1)
    return start, end


def is_temporal_query(text: str) -> bool:
    """Return whether a query should follow temporal recall routing."""
    lowered = text.casefold()
    return any(keyword in lowered for keyword in TEMPORAL_KEYWORDS)


def run_authoritative_recall(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int,
    known_item_lookup: KnownItemLookupFn,
    temporal_recall: TemporalRecallFn,
    topical_recall: TopicalRecallFn,
    mode: RecallMode = "auto",
    reference_time: datetime | None = None,
) -> tuple[list[SearchHit], RecallStrategy]:
    """Execute the canonical lexical recall routing contract."""
    if mode == "date":
        window = iso_date_window(query)
        if window is None:
            raise ValueError("date recall requires an ISO-8601 calendar date query.")
        start, end = window
        return (
            index.search(
                query,
                limit=limit,
                recorded_after=start,
                recorded_before=end,
            ),
            "date",
        )
    if mode == "temporal":
        return _run_temporal_recall(
            temporal_recall,
            index,
            query,
            limit=limit,
            reference_time=reference_time,
        )
    if mode == "known_item":
        return known_item_lookup(index, query, limit=limit), "known_item"
    if mode == "topic":
        return topical_recall(index, query, limit=limit), "topic"

    window = iso_date_window(query)
    if window is not None:
        start, end = window
        return (
            index.search(
                query,
                limit=limit,
                recorded_after=start,
                recorded_before=end,
            ),
            "date",
        )
    if is_temporal_query(query):
        return _run_temporal_recall(
            temporal_recall,
            index,
            query,
            limit=limit,
            reference_time=reference_time,
        )
    known_hits = known_item_lookup(index, query, limit=limit)
    if known_hits:
        return known_hits, "known_item"
    return topical_recall(index, query, limit=limit), "topic"


def _run_temporal_recall(
    temporal_recall: TemporalRecallFn,
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int,
    reference_time: datetime | None,
) -> tuple[list[SearchHit], Literal["temporal"]]:
    """Run temporal recall without widening required callable signatures."""
    if reference_time is None:
        return temporal_recall(index, query, limit=limit), "temporal"
    return (
        temporal_recall(
            index,
            query,
            limit=limit,
            reference_time=reference_time,
        ),
        "temporal",
    )


def normalize_lexical_hit(hit: Mapping[str, object]) -> NormalizedLexicalHit:
    """Normalize a surface hit payload to the shared lexical parity contract."""
    raw_terms = hit.get("matched_terms")
    matched_terms = (
        [str(term) for term in raw_terms if isinstance(term, str | int | float)]
        if isinstance(raw_terms, Sequence) and not isinstance(raw_terms, str)
        else []
    )
    raw_score = hit.get("score")
    score = float(raw_score) if isinstance(raw_score, int | float) else 0.0
    return {
        "kind": str(hit.get("kind") or ""),
        "matched_terms": matched_terms,
        "path": str(hit.get("path") or hit.get("id") or ""),
        "score": round(score, 6),
        "title": str(hit.get("title") or hit.get("path") or hit.get("id") or ""),
    }


def normalize_direct_search_hits(
    hits: Sequence[Mapping[str, object]],
) -> list[NormalizedLexicalHit]:
    """Normalize ordered direct-search hits for parity comparison."""
    return [normalize_lexical_hit(hit) for hit in hits]


def normalize_recall_hits(
    hits: Sequence[Mapping[str, object]],
) -> list[NormalizedLexicalHit]:
    """Normalize ordered authoritative recall hits for parity comparison."""
    return [normalize_lexical_hit(hit) for hit in hits]


def normalize_direct_search_result(
    payload: Mapping[str, object], *, hits_key: str = "hits"
) -> list[NormalizedLexicalHit]:
    """Normalize a direct-search result envelope for parity comparison."""
    raw_hits = payload.get(hits_key)
    if not isinstance(raw_hits, Sequence) or isinstance(raw_hits, str):
        return []
    normalized_hits: list[Mapping[str, object]] = [
        cast(Mapping[str, object], hit) for hit in raw_hits if isinstance(hit, Mapping)
    ]
    return normalize_direct_search_hits(normalized_hits)


def normalize_recall_result(
    payload: Mapping[str, object],
    *,
    hits_key: str = "hits",
    strategy_key: str = "strategy",
) -> NormalizedRecallParityResult:
    """Normalize an authoritative recall result envelope for parity comparison."""
    strategy = cast(RecallStrategy, str(payload.get(strategy_key) or "topic"))
    return {
        "hits": normalize_direct_search_result(payload, hits_key=hits_key),
        "strategy": strategy,
    }
