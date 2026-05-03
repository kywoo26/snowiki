from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from snowiki.schema.compiled import (
    CompiledPage,
    PageSection,
    PageType,
)
from snowiki.schema.normalized import NormalizedRecord
from snowiki.search.corpus import (
    runtime_corpus_from_mappings,
    runtime_corpus_from_records_and_pages,
    runtime_document_from_compiled_page,
    runtime_document_from_normalized_mapping,
    search_document_from_compiled_page,
    search_document_from_normalized_record,
)
from snowiki.search.models import SearchDocument
from snowiki.search.runtime_service import (
    RetrievalService,
    normalized_record_to_search_mapping,
)


def _normalized_record(**payload_overrides: object) -> NormalizedRecord:
    payload = {
        "title": "Runtime retrieval session",
        "content": "BM25SearchIndex and mixed retrieval work",
        "summary": "session summary",
        "aliases": ["BM25SearchIndex", "runtime retrieval"],
        **payload_overrides,
    }
    return NormalizedRecord(
        id="session-1",
        path="sessions/2026/session-1.json",
        source_type="claude",
        record_type="session",
        recorded_at="2026-04-07T12:00:00Z",
        payload=payload,
        raw_refs=[{"path": "raw/session-1.json"}],
    )


def _compiled_page(**overrides: object) -> CompiledPage:
    page = CompiledPage(
        page_type=PageType.TOPIC,
        slug="runtime-retrieval-architecture",
        title="Runtime retrieval architecture",
        created="2026-04-07T12:00:00Z",
        updated="2026-04-08T09:00:00Z",
        summary="BM25 runtime corpus",
        related=["compiled/topic/related.md"],
        tags=["retrieval", "bm25"],
        sections=[
            PageSection(
                title="Overview",
                body="SearchDocument keeps path and source_type fields.",
            )
        ],
        record_ids=["session-1"],
    )
    for key, value in overrides.items():
        setattr(page, key, value)
    return page


def test_search_document_from_normalized_record_preserves_identity() -> None:
    record = _normalized_record()

    document = search_document_from_normalized_record(record)

    assert document == SearchDocument(
        id="session-1",
        path="sessions/2026/session-1.json",
        kind="session",
        title="Runtime retrieval session",
        content=document.content,
        summary="session summary",
        aliases=("BM25SearchIndex", "runtime retrieval"),
        recorded_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        source_type="normalized",
        metadata=document.metadata,
    )
    assert document.content == "BM25SearchIndex and mixed retrieval work"
    assert "raw/session-1.json" not in document.content
    assert document.metadata["raw_ref"] == {"path": "raw/session-1.json"}


def test_search_document_from_compiled_page_preserves_page_fields() -> None:
    page = _compiled_page()

    document = search_document_from_compiled_page(page)

    assert document.kind == "page"
    assert document.source_type == "compiled"
    assert document.aliases == ("retrieval", "bm25")
    assert document.metadata["record_ids"] == ["session-1"]
    assert document.content == "Overview\nSearchDocument keeps path and source_type fields."
    assert "session-1" not in document.content


def test_runtime_document_from_normalized_mapping_preserves_identity() -> None:
    record = {
        "id": "session-1",
        "path": "sessions/2026/session-1.json",
        "title": "한국어 retrieval session",
        "record_type": "session",
        "recorded_at": "2026-04-07T12:00:00Z",
        "text": "BM25SearchIndex and 한국어 mixed retrieval work",
        "aliases": ["BM25SearchIndex", "한국어 검색"],
        "raw_ref": "raw/session-1.json",
    }

    document = runtime_document_from_normalized_mapping(record)

    assert document == SearchDocument(
        id="session-1",
        path="sessions/2026/session-1.json",
        kind="session",
        title="한국어 retrieval session",
        content=document.content,
        summary="session",
        aliases=("BM25SearchIndex", "한국어 검색"),
        recorded_at=datetime(2026, 4, 7, 12, 0, tzinfo=UTC),
        source_type="normalized",
        metadata=document.metadata,
    )
    assert document.content == "BM25SearchIndex and 한국어 mixed retrieval work"
    assert "raw/session-1.json" not in document.content
    assert document.metadata["raw_ref"] == "raw/session-1.json"


def test_runtime_document_from_compiled_page_preserves_page_fields() -> None:
    page = {
        "id": "compiled/wiki/search/runtime.md",
        "path": "compiled/wiki/search/runtime.md",
        "title": "Runtime retrieval architecture",
        "summary": "BM25 runtime corpus",
        "body": "SearchDocument keeps path and source_type fields.",
        "tags": ["retrieval", "bm25"],
        "updated_at": "2026-04-08T09:00:00Z",
        "record_ids": ["session-1"],
    }

    document = runtime_document_from_compiled_page(page)

    assert document.kind == "page"
    assert document.source_type == "compiled"
    assert document.aliases == ("retrieval", "bm25")
    assert document.metadata["record_ids"] == ["session-1"]
    assert document.content == "SearchDocument keeps path and source_type fields."
    assert "session-1" not in document.content


def test_runtime_corpus_from_records_and_pages_returns_search_documents_directly() -> None:
    corpus = runtime_corpus_from_records_and_pages(
        records=[_normalized_record()],
        pages=[_compiled_page()],
    )

    assert len(corpus) == 2
    assert all(isinstance(document, SearchDocument) for document in corpus)
    assert [document.kind for document in corpus] == ["session", "page"]
    assert corpus[0].metadata["id"] == "session-1"
    assert corpus[1].source_type == "compiled"


def test_runtime_corpus_returns_search_documents_directly() -> None:
    corpus = runtime_corpus_from_mappings(
        records=[{"id": "record-1", "path": "normalized/record-1.json"}],
        pages=[{"id": "page-1", "path": "compiled/page-1.md"}],
    )

    assert len(corpus) == 2
    assert all(isinstance(document, SearchDocument) for document in corpus)
    assert [document.kind for document in corpus] == ["session", "page"]
    assert corpus[0].metadata["id"] == "record-1"
    assert corpus[1].source_type == "compiled"


def test_runtime_corpus_search_documents_preserve_source_identity() -> None:
    record_doc = runtime_document_from_normalized_mapping(
        {"id": "record-1", "path": "normalized/record-1.json", "text": "hello"}
    )
    page_doc = runtime_document_from_compiled_page(
        {"id": "page-1", "path": "compiled/page-1.md", "body": "world"}
    )

    assert record_doc.kind == "session"
    assert record_doc.source_type == "normalized"
    assert record_doc.metadata["text"] == "hello"
    assert page_doc.kind == "page"
    assert page_doc.source_type == "compiled"
    assert page_doc.metadata["body"] == "world"


def test_runtime_corpus_metadata_includes_synthesized_defaults() -> None:
    record_doc = runtime_document_from_normalized_mapping(
        {"id": "record-1", "path": "normalized/record-1.json"}
    )
    page_doc = runtime_document_from_compiled_page(
        {"id": "page-1", "path": "compiled/page-1.md"}
    )

    assert record_doc.title == "record-1"
    assert record_doc.summary == "normalized record"
    assert record_doc.metadata["id"] == "record-1"
    assert record_doc.metadata["title"] == "record-1"
    assert record_doc.metadata["summary"] == "normalized record"
    assert page_doc.title == "compiled/page-1.md"
    assert page_doc.summary == "compiled wiki page"
    assert page_doc.metadata["path"] == "compiled/page-1.md"
    assert page_doc.metadata["title"] == "compiled/page-1.md"
    assert page_doc.metadata["summary"] == "compiled wiki page"


def test_search_document_searchable_texts_are_ordered_and_exclude_metadata() -> None:
    document = SearchDocument(
        id="doc-1",
        path="docs/runtime.md",
        kind="page",
        title="Runtime",
        summary="Search architecture",
        content="Primary body text",
        aliases=("bm25", "retrieval"),
        metadata={"hidden": "metadata should not be searchable"},
    )

    assert document.searchable_texts() == (
        "Runtime",
        "docs/runtime.md",
        "Search architecture",
        "Primary body text",
        "bm25 retrieval",
    )


def test_normalized_record_search_mapping_uses_only_primary_body_text() -> None:
    class _Record:
        def __init__(self) -> None:
            self.id = "record-1"
            self.path = "normalized/record-1.json"
            self.payload = {
                "title": "Record 1",
                "content": {"hidden": "metadata-only structure"},
                "body": ["Paragraph 1", "Paragraph 2"],
                "metadata": {"topic": "runtime"},
            }
            self.raw_refs = []
            self.record_type = "session"
            self.recorded_at = None

    mapping = normalized_record_to_search_mapping(cast(Any, _Record()))

    assert mapping["content"] == ""
    assert mapping["text"] == ""


def test_retrieval_service_uses_direct_typed_corpus_builder(
    monkeypatch: Any,
) -> None:
    calls: list[tuple[int, int]] = []

    def fake_direct_builder(
        *, records: list[NormalizedRecord], pages: list[CompiledPage]
    ) -> tuple[SearchDocument, ...]:
        calls.append((len(records), len(pages)))
        return (
            SearchDocument(
                id=records[0].id,
                path=records[0].path,
                kind="session",
                title="typed record",
                content="body",
                source_type="normalized",
            ),
            SearchDocument(
                id=pages[0].path,
                path=pages[0].path,
                kind="page",
                title="typed page",
                content="body",
                source_type="compiled",
            ),
        )

    def fail_mapping_builder(**_: object) -> tuple[SearchDocument, ...]:
        raise AssertionError("typed inputs should not use mapping corpus builder")

    monkeypatch.setattr(
        "snowiki.search.runtime_service.runtime_corpus_from_records_and_pages",
        fake_direct_builder,
    )
    monkeypatch.setattr(
        "snowiki.search.runtime_service.runtime_corpus_from_mappings",
        fail_mapping_builder,
    )

    snapshot = RetrievalService.from_records_and_pages(
        records=[_normalized_record()],
        pages=[_compiled_page()],
    )

    assert calls == [(1, 1)]
    assert snapshot.records_indexed == 1
    assert snapshot.pages_indexed == 1
    assert snapshot.index.size == 2
