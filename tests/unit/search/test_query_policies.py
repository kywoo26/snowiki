from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from snowiki.search.indexer import SearchDocument, SearchHit
from snowiki.search.queries.known_item import known_item_lookup
from snowiki.search.queries.temporal import temporal_recall
from snowiki.search.queries.topical import topical_recall
from snowiki.search.registry import SearchTokenizer, create


class RecordingIndex:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits: list[SearchHit] = hits
        self.calls: list[dict[str, object]] = []
        self._tokenizer: SearchTokenizer = create("regex_v1")

    @property
    def size(self) -> int:
        return len(self._hits)

    @property
    def tokenizer(self) -> SearchTokenizer:
        return self._tokenizer

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
        self.calls.append(
            {
                "query": query,
                "limit": limit,
                "kind_weights": kind_weights,
                "recorded_after": recorded_after,
                "recorded_before": recorded_before,
                "exact_path_bias": exact_path_bias,
            }
        )
        return self._hits[:limit]


class ReversingReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        self.calls.append((query, [hit.document.id for hit in hits]))
        return list(reversed(hits))


def _hit(document_id: str, *, kind: str = "page") -> SearchHit:
    return SearchHit(
        document=SearchDocument(
            id=document_id,
            path=f"{kind}/{document_id}.md",
            kind=kind,
            title=document_id,
            content=document_id,
        ),
        score=1.0,
        matched_terms=(document_id,),
    )


def test_known_item_lookup_uses_path_bias_session_weight_and_limit_multiplier() -> None:
    reranker = ReversingReranker()
    index = RecordingIndex([_hit("first"), _hit("second"), _hit("third")])

    hits = known_item_lookup(index, "config path", limit=2, reranker=reranker)

    assert [hit.document.id for hit in hits] == ["third", "second"]
    assert index.calls == [
        {
            "query": "config path",
            "limit": 6,
            "kind_weights": {"session": 1.15, "page": 0.85},
            "recorded_after": None,
            "recorded_before": None,
            "exact_path_bias": True,
        }
    ]
    assert reranker.calls == [("config path", ["first", "second", "third"])]


def test_topical_recall_uses_neutral_kind_weights_reranker_and_kind_blending() -> None:
    reranker = ReversingReranker()
    index = RecordingIndex(
        [
            _hit("session-1", kind="session"),
            _hit("session-2", kind="session"),
            _hit("page-1", kind="page"),
            _hit("page-2", kind="page"),
        ]
    )

    hits = topical_recall(index, "retrieval plan", limit=3, reranker=reranker)

    assert [hit.document.id for hit in hits] == ["page-2", "session-2", "page-1"]
    assert index.calls == [
        {
            "query": "retrieval plan",
            "limit": 12,
            "kind_weights": {"session": 1.0, "page": 1.0},
            "recorded_after": None,
            "recorded_before": None,
            "exact_path_bias": False,
        }
    ]
    assert reranker.calls == [
        ("retrieval plan", ["session-1", "session-2", "page-1", "page-2"])
    ]


def test_topical_recall_can_disable_kind_blending() -> None:
    reranker = ReversingReranker()
    index = RecordingIndex([_hit("first"), _hit("second"), _hit("third")])

    hits = topical_recall(
        index,
        "retrieval plan",
        limit=2,
        blend_kinds=False,
        reranker=reranker,
    )

    assert [hit.document.id for hit in hits] == ["third", "second"]


def test_temporal_recall_detects_yesterday_window_and_applies_limit_multiplier() -> None:
    reranker = ReversingReranker()
    index = RecordingIndex([_hit("old"), _hit("new")])
    reference_time = datetime(2026, 4, 8, 12, 30, tzinfo=UTC)

    hits = temporal_recall(
        index,
        "What did we do yesterday?",
        limit=1,
        reference_time=reference_time,
        reranker=reranker,
    )

    assert [hit.document.id for hit in hits] == ["new"]
    assert index.calls == [
        {
            "query": "What did we do yesterday?",
            "limit": 3,
            "kind_weights": None,
            "recorded_after": datetime(2026, 4, 7, tzinfo=UTC),
            "recorded_before": datetime(2026, 4, 8, tzinfo=UTC),
            "exact_path_bias": False,
        }
    ]
    assert reranker.calls == [("What did we do yesterday?", ["old", "new"])]


def test_temporal_recall_detects_this_week_window_from_week_start() -> None:
    index = RecordingIndex([_hit("week")])
    reference_time = datetime(2026, 4, 8, 12, 30, tzinfo=UTC)

    hits = temporal_recall(
        index,
        "이번주 검색 작업",
        reference_time=reference_time,
    )

    assert [hit.document.id for hit in hits] == ["week"]
    assert index.calls[0]["recorded_after"] == datetime(2026, 4, 6, tzinfo=UTC)
    assert index.calls[0]["recorded_before"] == datetime(
        2026, 4, 8, 12, 30, 1, tzinfo=UTC
    )


def test_temporal_recall_without_temporal_terms_searches_without_window() -> None:
    index = RecordingIndex([_hit("topic")])

    hits = temporal_recall(
        index,
        "retrieval architecture",
        reference_time=datetime(2026, 4, 8, 12, 30, tzinfo=UTC),
    )

    assert [hit.document.id for hit in hits] == ["topic"]
    assert index.calls[0]["recorded_after"] is None
    assert index.calls[0]["recorded_before"] is None
