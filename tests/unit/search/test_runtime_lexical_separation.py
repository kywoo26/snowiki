from __future__ import annotations

from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from snowiki.mcp.server import SnowikiReadOnlyFacade
from snowiki.search.indexer import InvertedIndex, SearchDocument
from snowiki.search.registry import SearchTokenizer
from snowiki.search.tokenizer import build_regex_tokenizer
from snowiki.search.workspace import RetrievalService


def _search_document(
    document_id: str,
    *,
    path: str,
    title: str,
    content: str = "",
    summary: str = "",
    aliases: tuple[str, ...] = (),
    kind: str = "note",
) -> SearchDocument:
    return SearchDocument(
        id=document_id,
        path=path,
        kind=kind,
        title=title,
        content=content,
        summary=summary,
        aliases=aliases,
    )


def test_retrieval_service_uses_runtime_lexical_builders_not_benchmark_indexes(
    mocker: MockerFixture,
) -> None:
    records: list[dict[str, object]] = [
        {
            "id": "session-1",
            "path": "normalized/session-1.json",
            "title": "Runtime lexical record",
            "content": "lexical runtime path",
        }
    ]
    pages: list[dict[str, object]] = [
        {
            "id": "page-1",
            "path": "compiled/topic/page-1.md",
            "title": "Runtime lexical page",
            "body": "page body",
        }
    ]
    call_log: list[dict[str, object]] = []
    lexical = SimpleNamespace(documents=("runtime-lexical-doc",))
    wiki = SimpleNamespace(documents=("runtime-wiki-doc",))
    blended = SimpleNamespace(size=2)

    def fake_build_lexical_index(normalized_records: list[dict[str, object]]) -> object:
        call_log.append({"fn": "build_lexical_index", "records": normalized_records})
        return lexical

    def fake_build_wiki_index(normalized_pages: list[dict[str, object]]) -> object:
        call_log.append({"fn": "build_wiki_index", "pages": normalized_pages})
        return wiki

    def fake_build_blended_index(*document_groups: tuple[str, ...]) -> object:
        call_log.append(
            {"fn": "build_blended_index", "document_groups": document_groups}
        )
        return blended

    def fail_bm25(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "runtime retrieval assembly must not instantiate benchmark BM25 indexes"
        )

    mocker.patch(
        "snowiki.search.workspace.build_lexical_index",
        side_effect=fake_build_lexical_index,
    )
    mocker.patch(
        "snowiki.search.workspace.build_wiki_index",
        side_effect=fake_build_wiki_index,
    )
    mocker.patch(
        "snowiki.search.workspace.build_blended_index",
        side_effect=fake_build_blended_index,
    )
    mocker.patch("snowiki.search.bm25_index.BM25SearchIndex", side_effect=fail_bm25)

    snapshot = RetrievalService.from_records_and_pages(records=records, pages=pages)

    assert snapshot.lexical is lexical
    assert snapshot.wiki is wiki
    assert snapshot.index is blended
    assert call_log == [
        {"fn": "build_lexical_index", "records": records},
        {"fn": "build_wiki_index", "pages": pages},
        {
            "fn": "build_blended_index",
            "document_groups": (
                ("runtime-lexical-doc",),
                ("runtime-wiki-doc",),
            ),
        },
    ]


def test_mcp_facade_uses_same_runtime_lexical_snapshot_not_benchmark_promotion(
    mocker: MockerFixture,
) -> None:
    session_records: list[dict[str, object]] = [
        {
            "id": "session-1",
            "path": "sessions/session-1.json",
            "title": "Session 1",
            "content": "runtime lexical session",
        }
    ]
    compiled_pages: list[dict[str, object]] = [
        {
            "id": "page-1",
            "path": "compiled/topics/runtime.md",
            "title": "Runtime topic",
            "body": "runtime page",
        }
    ]
    lexical = SimpleNamespace(documents=("runtime-lexical-doc",))
    wiki = SimpleNamespace(documents=("runtime-wiki-doc",))

    def search_index(query: str, limit: int = 5) -> list[object]:
        del query, limit
        return []

    blended = SimpleNamespace(search=search_index)
    snapshot = SimpleNamespace(
        lexical=lexical,
        wiki=wiki,
        index=blended,
        records_indexed=1,
        pages_indexed=1,
    )
    calls: list[dict[str, object]] = []

    def fake_from_records_and_pages(
        *, records: list[dict[str, object]], pages: list[dict[str, object]]
    ) -> object:
        calls.append({"records": records, "pages": pages})
        return snapshot

    mocker.patch(
        "snowiki.mcp.server.RetrievalService.from_records_and_pages",
        side_effect=fake_from_records_and_pages,
    )

    facade = SnowikiReadOnlyFacade(
        session_records=session_records,
        compiled_pages=compiled_pages,
    )

    assert facade.lexical_index is lexical
    assert facade.wiki_index is wiki
    assert facade.index is blended
    assert calls == [{"records": session_records, "pages": compiled_pages}]


def test_retrieval_service_threads_explicit_tokenizer_through_runtime_indexes() -> None:
    class RecordingTokenizer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def tokenize(self, text: str) -> tuple[str, ...]:
            self.calls.append(("tokenize", text))
            return tuple(text.casefold().split())

        def normalize(self, text: str) -> str:
            self.calls.append(("normalize", text))
            return text.casefold()

    tokenizer = RecordingTokenizer()
    records: list[dict[str, object]] = [
        {
            "id": "session-1",
            "path": "normalized/session-1.json",
            "title": "Runtime Tokenizer",
            "content": "alpha beta",
            "summary": "custom runtime seam",
        }
    ]
    pages: list[dict[str, object]] = [
        {
            "id": "page-1",
            "path": "compiled/runtime/page-1.md",
            "title": "Runtime Tokenizer Page",
            "body": "alpha gamma",
            "summary": "compiled runtime seam",
        }
    ]

    snapshot = RetrievalService.from_records_and_pages(
        records=records,
        pages=pages,
        tokenizer=tokenizer,
    )
    hits = snapshot.index.search("alpha")

    assert snapshot.lexical.index.tokenizer is tokenizer
    assert snapshot.wiki.index.tokenizer is tokenizer
    assert snapshot.index.tokenizer is tokenizer
    assert [hit.document.id for hit in hits] == ["page-1", "session-1"]
    assert ("tokenize", "alpha") in tokenizer.calls
    assert ("normalize", "alpha") in tokenizer.calls


def test_inverted_index_uses_injected_tokenizer_for_indexing_and_query_time() -> None:
    class ExactTokenizer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def tokenize(self, text: str) -> tuple[str, ...]:
            self.calls.append(("tokenize", text))
            if text == "special query":
                return ("special-token",)
            return (text.casefold().replace(" ", "-"),)

        def normalize(self, text: str) -> str:
            self.calls.append(("normalize", text))
            return text.casefold().replace(" ", "-")

    tokenizer = ExactTokenizer()
    snapshot = RetrievalService.from_records_and_pages(
        records=[
            {
                "id": "session-special",
                "path": "normalized/session-special.json",
                "title": "special token",
                "content": "special-token",
            }
        ],
        pages=[],
        tokenizer=tokenizer,
    )

    hits = snapshot.index.search("special query")

    assert [hit.document.id for hit in hits] == ["session-special"]
    assert tokenizer.calls.count(("tokenize", "special query")) == 1
    assert ("normalize", "special query") in tokenizer.calls


@pytest.mark.parametrize("query", ["", "!!! ... ---"])
def test_inverted_index_returns_no_hits_for_empty_or_zero_term_queries(
    query: str,
) -> None:
    index = InvertedIndex(
        [
            _search_document(
                "doc",
                path="notes/runtime.md",
                title="Runtime lexical document",
                content="searchable content",
            )
        ]
    )

    assert index.search(query) == []


def test_inverted_index_returns_no_hits_when_no_postings_match() -> None:
    index = InvertedIndex(
        [
            _search_document(
                "doc",
                path="notes/runtime.md",
                title="Runtime lexical document",
                content="searchable content",
            )
        ]
    )

    assert index.search("absent term") == []


def test_inverted_index_preserves_phrase_and_path_boost_scores() -> None:
    phrase_index = InvertedIndex(
        [
            _search_document(
                "phrase",
                path="notes/phrase.md",
                title="Alpha Beta",
            )
        ]
    )
    phrase_hit = phrase_index.search("alpha beta")[0]

    assert phrase_hit.document.id == "phrase"
    assert phrase_hit.score == 16.0
    assert phrase_hit.matched_terms == ("alpha", "alpha beta", "beta")

    path_index = InvertedIndex(
        [
            _search_document(
                "path",
                path="notes/alpha-beta.md",
                title="Path only",
            )
        ]
    )
    path_hit = path_index.search("alpha beta", exact_path_bias=True)[0]

    assert path_hit.document.id == "path"
    assert path_hit.score == 5.0 + (2 / 3 * 4.0) + 2.0
    assert path_hit.matched_terms == ("alpha", "beta")


def test_inverted_index_preserves_duplicate_query_term_scoring() -> None:
    class DuplicateTokenizer:
        def tokenize(self, text: str) -> tuple[str, ...]:
            if text == "alpha alpha":
                return ("alpha", "alpha")
            return tuple(part.casefold() for part in text.split() if part)

        def normalize(self, text: str) -> str:
            return text.casefold()

    index = InvertedIndex(
        [_search_document("doc", path="notes/doc.md", title="alpha")],
        tokenizer=DuplicateTokenizer(),
    )

    hit = index.search("alpha alpha")[0]

    assert hit.document.id == "doc"
    assert hit.score == 8.0
    assert hit.matched_terms == ("alpha",)


def test_inverted_index_preserves_zero_weight_ties_by_path_then_id() -> None:
    index = InvertedIndex(
        [
            _search_document("z-doc", path="notes/zeta.md", title="alpha"),
            _search_document("a-doc", path="notes/alpha.md", title="alpha"),
        ]
    )

    hits = index.search("alpha", kind_weights={"note": 0.0})

    assert [hit.document.id for hit in hits] == ["a-doc", "z-doc"]
    assert [hit.score for hit in hits] == [0.0, 0.0]


def test_inverted_index_handles_punctuation_mixed_case_unicode_and_mixed_language() -> None:
    index = InvertedIndex(
        [
            _search_document(
                "mixed",
                path="notes/Mixed-Language.md",
                title="Snowiki CAFÉ Retrieval",
                content="Runtime search handles 한국어 and English punctuation-heavy text.",
            )
        ]
    )

    hits = index.search("SNOWIKI!!! 한국어 café")

    assert [hit.document.id for hit in hits] == ["mixed"]
    assert "snowiki" in hits[0].matched_terms
    assert "한국어" in hits[0].matched_terms
    assert "caf" in hits[0].matched_terms


def test_inverted_index_search_does_not_normalize_candidate_documents_per_query() -> None:
    class CountingTokenizer:
        def __init__(self) -> None:
            self._inner: SearchTokenizer = build_regex_tokenizer()
            self.normalize_calls: list[str] = []

        def tokenize(self, text: str) -> tuple[str, ...]:
            return self._inner.tokenize(text)

        def normalize(self, text: str) -> str:
            self.normalize_calls.append(text)
            return self._inner.normalize(text)

    tokenizer = CountingTokenizer()
    index = InvertedIndex(
        [
            _search_document(
                f"doc-{index}",
                path=f"notes/common-{index}.md",
                title=f"Common title {index}",
                content="shared common body",
            )
            for index in range(6)
        ],
        tokenizer=tokenizer,
    )
    tokenizer.normalize_calls.clear()

    hits = index.search("common", limit=3)

    assert [hit.document.id for hit in hits] == ["doc-0", "doc-1", "doc-2"]
    assert tokenizer.normalize_calls == ["common"]
