from __future__ import annotations

from datetime import UTC, datetime

from snowiki.search.corpus import (
    RuntimeCorpusDocument,
    runtime_corpus_from_mappings,
    runtime_document_from_compiled_page,
    runtime_document_from_normalized_mapping,
)
from snowiki.search.index_lexical import normalized_record_to_document
from snowiki.search.index_wiki import compiled_page_to_document


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

    assert document == RuntimeCorpusDocument(
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
    assert "BM25SearchIndex and 한국어 mixed retrieval work" in document.content
    assert document.metadata["raw_ref"] == "raw/session-1.json"


def test_runtime_document_from_compiled_page_preserves_page_fields() -> None:
    page = {
        "id": "compiled/wiki/search/runtime.md",
        "path": "compiled/wiki/search/runtime.md",
        "title": "Runtime retrieval architecture",
        "summary": "BM25 runtime corpus",
        "body": "RuntimeCorpusDocument keeps path and source_type fields.",
        "tags": ["retrieval", "bm25"],
        "updated_at": "2026-04-08T09:00:00Z",
        "record_ids": ["session-1"],
    }

    document = runtime_document_from_compiled_page(page)

    assert document.kind == "page"
    assert document.source_type == "compiled"
    assert document.aliases == ("retrieval", "bm25")
    assert document.metadata["record_ids"] == ["session-1"]
    assert "RuntimeCorpusDocument keeps path" in document.content


def test_runtime_corpus_converts_to_search_and_bm25_documents() -> None:
    corpus = runtime_corpus_from_mappings(
        records=[{"id": "record-1", "path": "normalized/record-1.json"}],
        pages=[{"id": "page-1", "path": "compiled/page-1.md"}],
    )

    assert len(corpus) == 2
    assert [document.kind for document in corpus] == ["session", "page"]
    assert corpus[0].to_search_document().metadata["id"] == "record-1"
    assert corpus[1].to_bm25_document().source_type == "compiled"


def test_existing_index_builders_use_runtime_corpus_contract() -> None:
    record_doc = normalized_record_to_document(
        {"id": "record-1", "path": "normalized/record-1.json", "text": "hello"}
    )
    page_doc = compiled_page_to_document(
        {"id": "page-1", "path": "compiled/page-1.md", "body": "world"}
    )

    assert record_doc.kind == "session"
    assert record_doc.source_type == "normalized"
    assert record_doc.metadata["text"] == "hello"
    assert page_doc.kind == "page"
    assert page_doc.source_type == "compiled"
    assert page_doc.metadata["body"] == "world"


def test_runtime_corpus_metadata_includes_synthesized_defaults() -> None:
    record_doc = normalized_record_to_document(
        {"id": "record-1", "path": "normalized/record-1.json"}
    )
    page_doc = compiled_page_to_document(
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
