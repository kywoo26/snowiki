from __future__ import annotations

from datetime import UTC, datetime

from snowiki.search.corpus import RuntimeCorpusDocument
from snowiki.search.engine import BM25RuntimeIndex


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


def test_bm25_runtime_index_returns_search_hits_with_metadata() -> None:
    index = BM25RuntimeIndex(
        [
            RuntimeCorpusDocument(
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

    hits = index.search("bm25 runtime", limit=3)

    assert len(hits) == 1
    assert hits[0].document.id == "session-1"
    assert hits[0].document.metadata == {"raw_ref": "raw/session-1.json"}
    assert hits[0].document.source_type == "normalized"
    assert set(hits[0].matched_terms) >= {"bm25", "runtime"}


def test_bm25_runtime_index_applies_recorded_at_filters() -> None:
    index = BM25RuntimeIndex(
        [
            RuntimeCorpusDocument(
                id="old",
                path="sessions/old.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 4, 1, tzinfo=UTC),
            ),
            RuntimeCorpusDocument(
                id="new",
                path="sessions/new.json",
                kind="session",
                title="BM25 work",
                content="retrieval implementation",
                recorded_at=datetime(2026, 4, 8, tzinfo=UTC),
            ),
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search(
        "bm25 retrieval",
        recorded_after=datetime(2026, 4, 7, tzinfo=UTC),
    )

    assert [hit.document.id for hit in hits] == ["new"]


def test_bm25_runtime_index_applies_kind_weights_and_path_bias() -> None:
    index = BM25RuntimeIndex(
        [
            RuntimeCorpusDocument(
                id="session",
                path="sessions/search-plan.json",
                kind="session",
                title="Search plan",
                content="alpha beta",
            ),
            RuntimeCorpusDocument(
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
        "search plan",
        kind_weights={"session": 0.5, "page": 2.0},
        exact_path_bias=True,
        limit=2,
    )

    assert [hit.document.id for hit in hits] == ["page", "session"]


def test_bm25_runtime_index_uses_injected_tokenizer_for_runtime_queries() -> None:
    index = BM25RuntimeIndex(
        [
            RuntimeCorpusDocument(
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

    hits = index.search("프로시저", limit=1)

    assert [hit.document.id for hit in hits] == ["ko-page"]
    assert hits[0].matched_terms == ("procedure",)


def test_bm25_runtime_index_indexes_paths_for_known_item_queries() -> None:
    index = BM25RuntimeIndex(
        [
            RuntimeCorpusDocument(
                id="path-doc",
                path="compiled/special-path.md",
                kind="page",
                title="Unrelated title",
                content="Unrelated content",
            )
        ],
        tokenizer_name="regex_v1",
    )

    hits = index.search("special-path.md", exact_path_bias=True, limit=1)

    assert [hit.document.id for hit in hits] == ["path-doc"]
