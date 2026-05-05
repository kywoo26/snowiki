from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snowiki.compiler.engine import CompilerEngine
from snowiki.schema.compiled import CompiledPage
from snowiki.schema.normalized import NormalizedRecord

from .corpus import (
    page_body,
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
        records: list[NormalizedRecord],
        pages: list[CompiledPage],
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot:
        resolved_tokenizer = tokenizer or create_tokenizer(default().name)
        runtime_tokenizer_name = getattr(resolved_tokenizer, "name", default().name)
        if not isinstance(runtime_tokenizer_name, str):
            runtime_tokenizer_name = default().name
        corpus = runtime_corpus_from_records_and_pages(
            records=records,
            pages=pages,
        )
        return RetrievalSnapshot(
            index=BM25RuntimeIndex(
                corpus,
                tokenizer_name=runtime_tokenizer_name,
                tokenizer=resolved_tokenizer,
            ),
            records_indexed=len(records),
            pages_indexed=len(pages),
        )


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
