from __future__ import annotations

from types import SimpleNamespace

from pytest_mock import MockerFixture

from snowiki.mcp.server import SnowikiReadOnlyFacade
from snowiki.search.workspace import RetrievalService


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
