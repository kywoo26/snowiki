from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.schema.compiled import CompiledPage
from snowiki.schema.normalized import NormalizedRecord

from .corpus import (
    page_body,
    runtime_corpus_from_mappings,
    runtime_corpus_from_records_and_pages,
)
from .engine import BM25RuntimeIndex
from .protocols import RuntimeSearchIndex
from .registry import SearchTokenizer, default
from .registry import create as create_tokenizer


def _primary_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, list | tuple):
        return "\n".join(text for item in value if (text := _primary_text(item)))
    return ""


def compiled_page_to_search_mapping(page: CompiledPage) -> dict[str, object]:
    """Compatibility wrapper for dict-based compiled page callers."""

    return {
        "id": page.path,
        "path": page.path,
        "title": page.title,
        "summary": page.summary,
        "body": page_body(page.sections),
        "tags": page.tags,
        "related": page.related,
        "record_ids": page.record_ids,
        "updated_at": page.updated,
    }


def normalized_record_to_search_mapping(record: NormalizedRecord) -> dict[str, Any]:
    """Compatibility wrapper for dict-based normalized record callers."""

    metadata = record.payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, dict) else {}
    title = ""
    if metadata_map:
        title = str(metadata_map.get("title") or metadata_map.get("name") or "").strip()
    title = title or str(record.payload.get("title") or record.id)
    content_value = (
        record.payload.get("content")
        or record.payload.get("text")
        or record.payload.get("body")
    )
    content = _primary_text(content_value)
    raw_ref = record.raw_refs[0] if record.raw_refs else None
    return {
        **record.payload,
        "id": record.id,
        "path": record.path,
        "title": title,
        "content": content,
        "text": content,
        "metadata": metadata_map,
        "raw_ref": raw_ref,
        "record_type": record.record_type,
        "recorded_at": record.recorded_at,
    }


@dataclass(frozen=True, slots=True)
class RetrievalSnapshot:
    index: RuntimeSearchIndex
    records_indexed: int
    pages_indexed: int


class RetrievalService:
    """Canonical retrieval assembly service."""

    @classmethod
    def from_root(
        cls,
        root: Path,
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot:
        compiler = CompilerEngine(root)
        records = compiler.load_normalized_records()
        pages = compiler.build_pages(records) if records else []
        return cls.from_records_and_pages(
            records=records,
            pages=pages,
            tokenizer=tokenizer,
        )

    @classmethod
    def from_records_and_pages(
        cls,
        *,
        records: list[NormalizedRecord] | list[dict[str, Any]],
        pages: list[CompiledPage] | list[dict[str, object]],
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot:
        typed_records = cls._typed_records(records)
        typed_pages = cls._typed_pages(pages)
        mapping_records = cls._mapping_records(records)
        mapping_pages = cls._mapping_pages(pages)
        resolved_tokenizer = tokenizer or create_tokenizer(default().name)
        runtime_tokenizer_name = getattr(resolved_tokenizer, "name", default().name)
        if not isinstance(runtime_tokenizer_name, str):
            runtime_tokenizer_name = default().name
        if typed_records is not None and typed_pages is not None:
            corpus = runtime_corpus_from_records_and_pages(
                records=typed_records,
                pages=typed_pages,
            )
        elif mapping_records is not None and mapping_pages is not None:
            corpus = runtime_corpus_from_mappings(
                records=mapping_records,
                pages=mapping_pages,
            )
        elif typed_records is not None and mapping_pages is not None:
            corpus = runtime_corpus_from_records_and_pages(
                records=typed_records,
                pages=[],
            ) + runtime_corpus_from_mappings(records=[], pages=mapping_pages)
        elif mapping_records is not None and typed_pages is not None:
            corpus = runtime_corpus_from_mappings(
                records=mapping_records,
                pages=[],
            ) + runtime_corpus_from_records_and_pages(records=[], pages=typed_pages)
        else:
            raise TypeError("records and pages must each be homogeneous typed objects or mappings")
        return RetrievalSnapshot(
            index=BM25RuntimeIndex(
                corpus,
                tokenizer_name=runtime_tokenizer_name,
                tokenizer=resolved_tokenizer,
            ),
            records_indexed=len(records),
            pages_indexed=len(pages),
        )

    @staticmethod
    def _typed_records(
        records: list[NormalizedRecord] | list[dict[str, Any]],
    ) -> list[NormalizedRecord] | None:
        if not records:
            return []
        if all(isinstance(record, NormalizedRecord) for record in records):
            return cast(list[NormalizedRecord], records)
        if all(isinstance(record, dict) for record in records):
            return None
        raise TypeError("records must be homogeneous normalized records or mappings")

    @staticmethod
    def _mapping_records(
        records: list[NormalizedRecord] | list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        if not records:
            return []
        if all(isinstance(record, dict) for record in records):
            return [dict(record) for record in cast(list[dict[str, Any]], records)]
        if all(isinstance(record, NormalizedRecord) for record in records):
            return None
        raise TypeError("records must be homogeneous normalized records or mappings")

    @staticmethod
    def _typed_pages(
        pages: list[CompiledPage] | list[dict[str, object]],
    ) -> list[CompiledPage] | None:
        if not pages:
            return []
        if all(isinstance(page, CompiledPage) for page in pages):
            return cast(list[CompiledPage], pages)
        if all(isinstance(page, dict) for page in pages):
            return None
        raise TypeError("pages must be homogeneous compiled pages or mappings")

    @staticmethod
    def _mapping_pages(
        pages: list[CompiledPage] | list[dict[str, object]],
    ) -> list[dict[str, object]] | None:
        if not pages:
            return []
        if all(isinstance(page, dict) for page in pages):
            return [dict(page) for page in cast(list[dict[str, object]], pages)]
        if all(isinstance(page, CompiledPage) for page in pages):
            return None
        raise TypeError("pages must be homogeneous compiled pages or mappings")


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
