from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection

from .index_lexical import build_lexical_index
from .index_wiki import build_wiki_index
from .indexer import InvertedIndex, build_blended_index


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


def build_search_index(root: Path) -> tuple[InvertedIndex, int, int]:
    compiler = CompilerEngine(root)
    records = compiler.load_normalized_records()
    pages = compiler.build_pages(records) if records else []
    lexical = build_lexical_index(
        normalized_record_to_search_mapping(record) for record in records
    )
    wiki = build_wiki_index(compiled_page_to_search_mapping(page) for page in pages)
    return (
        build_blended_index(lexical.documents, wiki.documents),
        len(records),
        len(pages),
    )


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
