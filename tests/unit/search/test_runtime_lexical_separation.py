from __future__ import annotations

from types import SimpleNamespace

from pytest_mock import MockerFixture

from snowiki.mcp.server import SnowikiReadOnlyFacade
from snowiki.search.engine import BM25RuntimeIndex
from snowiki.search.models import SearchDocument
from snowiki.search.requests import RuntimeSearchRequest
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


def test_retrieval_service_builds_primary_bm25_runtime_index() -> None:
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
    snapshot = RetrievalService.from_records_and_pages(records=records, pages=pages)

    assert isinstance(snapshot.index, BM25RuntimeIndex)
    assert snapshot.index.size == 2
    assert snapshot.records_indexed == 1
    assert snapshot.pages_indexed == 1


def test_mcp_facade_uses_same_runtime_snapshot_index(
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
    def search_index(query: str, limit: int = 5) -> list[object]:
        del query, limit
        return []

    runtime_index = SimpleNamespace(search=search_index)
    snapshot = SimpleNamespace(
        index=runtime_index,
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

    assert facade.index is runtime_index
    assert not hasattr(facade, "lexical_index")
    assert not hasattr(facade, "wiki_index")
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
    request = RuntimeSearchRequest(query="alpha", candidate_limit=10)
    hits = snapshot.index.search(request)

    assert snapshot.index.tokenizer is tokenizer
    assert {hit.document.id for hit in hits} == {"page-1", "session-1"}
    assert ("tokenize", "alpha") in tokenizer.calls
    assert ("normalize", "alpha") in tokenizer.calls


def test_runtime_index_uses_injected_tokenizer_for_indexing_and_query_time() -> None:
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

    request = RuntimeSearchRequest(query="special query", candidate_limit=10)
    hits = snapshot.index.search(request)

    assert [hit.document.id for hit in hits] == ["session-special"]
    assert tokenizer.calls.count(("tokenize", "special query")) >= 1
    assert ("normalize", "special query") in tokenizer.calls
