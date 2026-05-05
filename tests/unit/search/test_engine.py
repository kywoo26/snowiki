from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import TypedDict

from snowiki.bench.specs import BenchmarkQuery
from snowiki.benchmark_targets import (
    BENCHMARK_RETRIEVAL_LIMIT,
    _run_snowiki_query_runtime,
)
from snowiki.search.engine import BM25RuntimeIndex
from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.queries.topical import execute_topical_search
from snowiki.search.requests import RuntimeSearchRequest
from snowiki.search.scoring import SearchRuntimeTokenizer


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
    query: str
    document_id: str
    document_terms: set[str]
    exact_path_bias: bool
    kind_weights: Mapping[str, float] | None


class RecordingScoringPolicy:
    def __init__(self) -> None:
        self.calls: list[_PolicyCall] = []

    def rank_candidates(
        self,
        candidates: Iterable[SearchHit],
        *,
        query: str,
        tokenizer: SearchRuntimeTokenizer,
        document_tokens: Callable[[str], tuple[str, ...]],
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for candidate in candidates:
            hit = self.score_candidate(
                document=candidate.document,
                raw_score=candidate.score,
                query_tokens=tokenizer.tokenize(query),
                document_tokens=document_tokens(candidate.document.id),
                tokenizer=tokenizer,
                query=query,
                exact_path_bias=exact_path_bias,
                kind_weights=kind_weights,
            )
            if hit is not None:
                hits.append(hit)
        return hits

    def score_candidate(
        self,
        *,
        document: SearchDocument,
        raw_score: float,
        query_tokens: tuple[str, ...],
        document_tokens: tuple[str, ...],
        tokenizer: SearchRuntimeTokenizer,
        query: str,
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> SearchHit | None:
        _ = tokenizer
        query_terms = set(query_tokens)
        self.calls.append(
            {
                "query": query,
                "document_id": document.id,
                "document_terms": set(document_tokens),
                "exact_path_bias": exact_path_bias,
                "kind_weights": kind_weights,
            }
        )
        return SearchHit(
            document=document,
            score=raw_score,
            matched_terms=tuple(sorted(query_terms & set(document_tokens))),
        )

    def sort_key(self, hit: SearchHit) -> tuple[float, float, str, str]:
        return (-hit.score, 0.0, hit.document.path, hit.document.id)


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


def test_bm25_runtime_index_returns_empty_when_no_documents_match() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="doc",
                path="pages/doc.md",
                kind="page",
                title="Runtime notes",
                content="retrieval implementation",
            )
        ],
        tokenizer_name="regex_v1",
    )

    assert index.search(RuntimeSearchRequest(query="absent", candidate_limit=3)) == []


def test_bm25_runtime_index_allows_top_k_larger_than_matching_corpus() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="doc-a",
                path="pages/a.md",
                kind="page",
                title="Runtime notes",
                content="shared retrieval alpha",
            ),
            SearchDocument(
                id="doc-b",
                path="pages/b.md",
                kind="page",
                title="Runtime notes",
                content="shared retrieval beta",
            ),
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(RuntimeSearchRequest(query="shared retrieval", candidate_limit=20))

    assert [hit.document.id for hit in hits] == ["doc-a", "doc-b"]


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


def test_bm25_runtime_index_returns_empty_when_recorded_at_filter_excludes_all() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="old",
                path="sessions/old.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            )
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

    assert hits == []


def test_bm25_runtime_index_orders_tied_candidates_by_path_then_id() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="b",
                path="pages/shared.md",
                kind="page",
                title="Runtime notes",
                content="same lexical evidence",
            ),
            SearchDocument(
                id="a",
                path="pages/shared.md",
                kind="page",
                title="Runtime notes",
                content="same lexical evidence",
            ),
            SearchDocument(
                id="z",
                path="pages/alpha.md",
                kind="page",
                title="Runtime notes",
                content="same lexical evidence",
            ),
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(RuntimeSearchRequest(query="same lexical", candidate_limit=3))

    assert [(hit.document.path, hit.document.id) for hit in hits] == [
        ("pages/alpha.md", "z"),
        ("pages/shared.md", "a"),
        ("pages/shared.md", "b"),
    ]


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


def test_bm25_runtime_index_provides_raw_runtime_evidence_to_scoring_policy() -> None:
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
        scoring_policy=policy,
    )

    hits = index.search(
        RuntimeSearchRequest(
            query="special",
            candidate_limit=1,
            exact_path_bias=True,
            kind_weights={"page": 1.25},
        )
    )

    assert [hit.document.id for hit in hits] == ["path-doc"]
    assert hits[0].matched_terms == ("special",)
    assert len(policy.calls) == 1
    call = policy.calls[0]
    assert call["query"] == "special"
    assert call["document_id"] == "path-doc"
    assert "special" in call["document_terms"]
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


def test_benchmark_runtime_target_matches_canonical_topical_order() -> None:
    index = BM25RuntimeIndex(
        [
            SearchDocument(
                id="doc-a",
                path="benchmark/doc-a.md",
                kind="benchmark_doc",
                title="Alpha topic",
                content="needle alpha",
            ),
            SearchDocument(
                id="doc-b",
                path="benchmark/doc-b.md",
                kind="benchmark_doc",
                title="Needle alpha phrase",
                content="needle alpha phrase",
            ),
            SearchDocument(
                id="doc-c",
                path="benchmark/doc-c.md",
                kind="benchmark_doc",
                title="Needle only",
                content="needle only",
            ),
        ],
        tokenizer_name="regex_v1",
    )
    query = BenchmarkQuery(query_id="q1", query_text="needle alpha")

    canonical_ids = tuple(
        hit.document.id
        for hit in execute_topical_search(
            index,
            query.query_text,
            limit=BENCHMARK_RETRIEVAL_LIMIT,
        )
    )
    benchmark_result = _run_snowiki_query_runtime(index=index, query=query)

    assert benchmark_result.ranked_doc_ids == canonical_ids
