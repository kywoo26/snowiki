from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TypedDict

from snowiki.search.engine import BM25RuntimeIndex
from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.requests import RuntimeSearchRequest


class SynonymTokenizer:
    def tokenize(self, text: str) -> tuple[str, ...]:
        terms: list[str] = []
        for token in text.lower().replace(".", " ").split():
            if token in {"절차", "프로시저"}:
                terms.append("procedure")
            else:
                terms.append(token)
        return tuple(terms)

    def normalize(self, text: str) -> str:
        return " ".join(self.tokenize(text))


class _PolicyCall(TypedDict):
    document_id: str
    query_terms: set[str]
    document_terms: set[str]
    normalized_query: str
    normalized_path: str
    exact_path_bias: bool
    kind_weights: Mapping[str, float] | None


class RecordingScoringPolicy:
    def __init__(self) -> None:
        self.calls: list[_PolicyCall] = []

    def score_candidate(
        self,
        *,
        document: SearchDocument,
        raw_score: float,
        query_terms: set[str],
        document_terms: set[str],
        normalized_query: str,
        normalized_path: str,
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> SearchHit | None:
        self.calls.append(
            {
                "document_id": document.id,
                "query_terms": query_terms,
                "document_terms": document_terms,
                "normalized_query": normalized_query,
                "normalized_path": normalized_path,
                "exact_path_bias": exact_path_bias,
                "kind_weights": kind_weights,
            }
        )
        return SearchHit(
            document=document,
            score=raw_score,
            matched_terms=tuple(sorted(query_terms & document_terms)),
        )

    def sort_key(self, hit: SearchHit) -> tuple[float, str, str]:
        return (-hit.score, hit.document.path, hit.document.id)


def test_bm25_runtime_index_returns_search_hits_with_metadata() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="session-1",
                path="sessions/session-1.json",
                kind="session",
                title="Runtime BM25 session",
                content="bm25 runtime metadata payload",
                summary="Runtime summary",
                source_type="normalized",
                metadata={"raw_ref": "raw/session-1.json"},
            )
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(RuntimeSearchRequest(query="bm25 runtime", candidate_limit=3))

    assert len(hits) == 1
    assert hits[0].document.id == "session-1"
    assert hits[0].document.metadata == {"raw_ref": "raw/session-1.json"}
    assert hits[0].document.source_type == "normalized"
    assert set(hits[0].matched_terms) >= {"bm25", "runtime"}


def test_bm25_runtime_index_returns_empty_for_blank_query_or_zero_limit() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="doc",
                path="pages/doc.md",
                kind="page",
                title="BM25 runtime",
                content="retrieval implementation",
            )
        ],
        tokenizer_name="regex_v1",
    )

    assert index.search(RuntimeSearchRequest(query="bm25", candidate_limit=0)) == []
    assert index.search(RuntimeSearchRequest(query="", candidate_limit=3)) == []
    assert index.search(RuntimeSearchRequest(query="   ", candidate_limit=3)) == []


def test_bm25_runtime_index_applies_recorded_at_filters() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="old",
                path="sessions/old.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
            SearchDocument(
                id="new",
                path="sessions/new.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 4, 8, tzinfo=UTC),
            ),
            SearchDocument(
                id="future",
                path="sessions/future.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 5, 1, tzinfo=UTC),
            ),
            SearchDocument(
                id="undated",
                path="sessions/undated.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
            ),
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(
        RuntimeSearchRequest(
            query="bm25 retrieval",
            candidate_limit=4,
            recorded_after=datetime(2026, 4, 7, tzinfo=UTC),
            recorded_before=datetime(2026, 4, 30, tzinfo=UTC),
        )
    )

    assert [hit.document.id for hit in hits] == ["new"]


def test_bm25_runtime_index_applies_policy_sorting_and_scoring() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="session",
                path="sessions/search-plan.json",
                kind="session",
                title="Search plan",
                content="alpha beta",
            ),
            SearchDocument(
                id="page",
                path="compiled/search-plan.md",
                kind="page",
                title="Search plan",
                content="alpha beta",
            ),
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(
        RuntimeSearchRequest(
            query="search plan",
            candidate_limit=2,
            kind_weights={"session": 0.5, "page": 2.0},
            exact_path_bias=True,
        )
    )

    assert [hit.document.id for hit in hits] == ["page", "session"]


def test_bm25_runtime_index_provides_token_evidence_to_scoring_policy() -> None:
    policy = RecordingScoringPolicy()
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="path-doc",
                path="compiled/special.md",
                kind="page",
                title="Unrelated title",
                content="Unrelated content",
            )
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(
        RuntimeSearchRequest(
            query="special",
            candidate_limit=1,
            exact_path_bias=True,
            kind_weights={"page": 1.25},
            scoring_policy=policy,
        )
    )

    assert [hit.document.id for hit in hits] == ["path-doc"]
    assert hits[0].matched_terms == ("special",)
    assert len(policy.calls) == 1
    call = policy.calls[0]
    assert call["document_id"] == "path-doc"
    assert call["query_terms"] == {"special"}
    assert "special" in call["document_terms"]
    assert call["normalized_query"] == "special"
    assert call["normalized_path"] == "compiled/special.md"
    assert call["exact_path_bias"] is True
    assert call["kind_weights"] == {"page": 1.25}


def test_bm25_runtime_index_uses_injected_tokenizer_for_runtime_queries() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="ko-page",
                path="compiled/ko-page.md",
                kind="page",
                title="Korean workflow",
                content="절차 설명",
            )
        ],
        tokenizer=SynonymTokenizer(),
        tokenizer_name="regex_v1",
    )

    hits = index.search(RuntimeSearchRequest(query="프로시저", candidate_limit=1))

    assert [hit.document.id for hit in hits] == ["ko-page"]
    assert hits[0].matched_terms == ("procedure",)
