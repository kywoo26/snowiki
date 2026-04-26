from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..indexer import SearchHit
from ..protocols import RuntimeSearchIndex
from ..rerank import NoOpReranker, Reranker


@dataclass(frozen=True)
class TemporalWindow:
    start: datetime | None
    end: datetime | None


def _detect_temporal_window(query: str, *, reference_time: datetime) -> TemporalWindow:
    lowered = query.casefold()
    day_start = reference_time.replace(hour=0, minute=0, second=0, microsecond=0)

    if any(token in lowered for token in ("yesterday", "어제")):
        start = day_start - timedelta(days=1)
        return TemporalWindow(start=start, end=day_start)
    if any(token in lowered for token in ("today", "오늘", "recent", "최근")):
        return TemporalWindow(
            start=day_start, end=reference_time + timedelta(seconds=1)
        )
    if any(token in lowered for token in ("last week", "지난주")):
        start = day_start - timedelta(days=7)
        return TemporalWindow(start=start, end=reference_time + timedelta(seconds=1))
    if any(token in lowered for token in ("this week", "이번주")):
        weekday_start = day_start - timedelta(days=day_start.weekday())
        return TemporalWindow(
            start=weekday_start, end=reference_time + timedelta(seconds=1)
        )
    return TemporalWindow(start=None, end=None)


def temporal_recall(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    reference_time: datetime | None = None,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    reranker = reranker or NoOpReranker()
    reference_time = reference_time or datetime.now(tz=UTC)
    window = _detect_temporal_window(query, reference_time=reference_time)
    hits = index.search(
        query,
        limit=limit * 3,
        recorded_after=window.start,
        recorded_before=window.end,
    )
    return reranker.rerank(query, hits)[:limit]
