from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime

import pytest

from snowiki.schema.compiled import (
    CompiledPage,
    PageSection,
    PageType,
)
from snowiki.schema.normalized import NormalizedRecord
from snowiki.search.corpus import (
    runtime_corpus_from_records_and_pages,
    search_document_from_compiled_page,
    search_document_from_normalized_record,
)
from snowiki.search.models import SearchDocument
from snowiki.search.runtime_service import RetrievalService


def test_search_document_fields_match_typed_corpus_contract() -> None:
    assert [field.name for field in fields(SearchDocument)] == [
        "id",
        "path",
        "kind",
        "title",
        "content",
        "summary",
        "aliases",
        "recorded_at",
        "source_type",
        "metadata",
    ]


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
    assert (
        document.content
        == "Overview\nSearchDocument keeps path and source_type fields."
    )
    assert "session-1" not in document.content


def test_runtime_corpus_from_records_and_pages_returns_search_documents_directly() -> (
    None
):
    record = _normalized_record()
    page = _compiled_page()

    corpus = runtime_corpus_from_records_and_pages(
        records=[record],
        pages=[page],
    )

    assert corpus == (
        search_document_from_normalized_record(record),
        search_document_from_compiled_page(page),
    )
    assert len(corpus) == 2
    assert all(isinstance(document, SearchDocument) for document in corpus)
    assert [document.kind for document in corpus] == ["session", "page"]
    assert corpus[0].metadata["id"] == "session-1"
    assert corpus[1].source_type == "compiled"


def test_runtime_corpus_from_empty_typed_inputs_returns_empty_tuple() -> None:
    records: list[NormalizedRecord] = []
    pages: list[CompiledPage] = []

    assert runtime_corpus_from_records_and_pages(records=records, pages=pages) == ()


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


def test_retrieval_service_rejects_dict_records() -> None:
    with pytest.raises(TypeError, match="typed NormalizedRecord instances"):
        RetrievalService.from_records_and_pages(
            records=[{"id": "test"}], pages=[]  # type: ignore
        )


def test_retrieval_service_rejects_dict_pages() -> None:
    with pytest.raises(TypeError, match="typed CompiledPage instances"):
        RetrievalService.from_records_and_pages(
            records=[], pages=[{"id": "test"}]  # type: ignore
        )


def test_retrieval_service_rejects_mixed_typed_and_dict_records() -> None:
    record = _normalized_record()
    with pytest.raises(TypeError, match="typed NormalizedRecord instances"):
        RetrievalService.from_records_and_pages(
            records=[record, {"id": "test"}], pages=[]  # type: ignore
        )


def test_retrieval_service_uses_direct_typed_corpus_builder(
    monkeypatch: pytest.MonkeyPatch,
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

    monkeypatch.setattr(
        "snowiki.search.runtime_service.runtime_corpus_from_records_and_pages",
        fake_direct_builder,
    )

    snapshot = RetrievalService.from_records_and_pages(
        records=[_normalized_record()],
        pages=[_compiled_page()],
    )

    assert calls == [(1, 1)]
    assert snapshot.records_indexed == 1
    assert snapshot.pages_indexed == 1
    assert snapshot.index.size == 2
