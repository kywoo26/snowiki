from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection

from .corpus import runtime_corpus_from_mappings
from .engine import BM25RuntimeIndex
from .protocols import RuntimeSearchIndex
from .registry import SearchTokenizer, default
from .registry import create as create_tokenizer


def page_body(sections: list[PageSection]) -> str:
    return "\n\n".join(f"{section.title}\n{section.body}" for section in sections)


def compiled_page_to_search_mapping(page: CompiledPage) -> dict[str, object]:
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
    metadata = record.payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, dict) else {}
    title = ""
    if metadata_map:
        title = str(metadata_map.get("title") or metadata_map.get("name") or "").strip()
    title = title or str(record.payload.get("title") or record.id)
    content_value = record.payload.get("content") or record.payload.get("text")
    if isinstance(content_value, str):
        content = content_value
    else:
        content = json.dumps(
            content_value if content_value is not None else record.payload,
            ensure_ascii=False,
            sort_keys=True,
        )
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
        normalized_records = cls._normalize_records(records)
        normalized_pages = cls._normalize_pages(pages)
        resolved_tokenizer = tokenizer or create_tokenizer(default().name)
        runtime_tokenizer_name = getattr(resolved_tokenizer, "name", default().name)
        if not isinstance(runtime_tokenizer_name, str):
            runtime_tokenizer_name = default().name
        corpus = runtime_corpus_from_mappings(
            records=normalized_records,
            pages=normalized_pages,
        )
        return RetrievalSnapshot(
            index=BM25RuntimeIndex(
                corpus,
                tokenizer_name=runtime_tokenizer_name,
                tokenizer=resolved_tokenizer,
            ),
            records_indexed=len(normalized_records),
            pages_indexed=len(normalized_pages),
        )

    @staticmethod
    def _normalize_records(
        records: list[NormalizedRecord] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not records:
            return []
        if all(isinstance(record, NormalizedRecord) for record in records):
            return [
                normalized_record_to_search_mapping(record)
                for record in cast(list[NormalizedRecord], records)
            ]
        if all(isinstance(record, dict) for record in records):
            return [dict(record) for record in cast(list[dict[str, Any]], records)]
        raise TypeError("records must be homogeneous normalized records or mappings")

    @staticmethod
    def _normalize_pages(
        pages: list[CompiledPage] | list[dict[str, object]],
    ) -> list[dict[str, object]]:
        if not pages:
            return []
        if all(isinstance(page, CompiledPage) for page in pages):
            return [
                compiled_page_to_search_mapping(page)
                for page in cast(list[CompiledPage], pages)
            ]
        if all(isinstance(page, dict) for page in pages):
            return [dict(page) for page in cast(list[dict[str, object]], pages)]
        raise TypeError("pages must be homogeneous compiled pages or mappings")


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
