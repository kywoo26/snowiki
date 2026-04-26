from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection

from .corpus import runtime_corpus_from_mappings
from .engine import BM25RuntimeIndex
from .protocols import RuntimeSearchIndex
from .registry import (
    SearchTokenizer,
    default,
    get,
)
from .registry import create as create_tokenizer
from .tokenizer_compat import (
    StaleTokenizerArtifactError,
    require_tokenizer_compatibility,
)


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


def current_runtime_tokenizer_name() -> str:
    """Return the canonical tokenizer identity for runtime retrieval."""
    return default().name


def validate_runtime_manifest_tokenizer(root: Path) -> str | None:
    """Fail closed when a stored runtime manifest has stale tokenizer identity."""
    manifest_path = root.resolve() / "index" / "manifest.json"
    if not manifest_path.exists():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StaleTokenizerArtifactError(
            artifact_path=manifest_path,
            requested_tokenizer_name=current_runtime_tokenizer_name(),
            stored_tokenizer_name=None,
        )
    return require_tokenizer_compatibility(
        artifact_path=manifest_path,
        requested_tokenizer_name=current_runtime_tokenizer_name(),
        metadata=payload,
    )


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


def _tree_signature(root: Path) -> tuple[int, int]:
    if not root.exists():
        return (0, 0)
    latest_mtime = root.stat().st_mtime_ns
    file_count = 0
    for path in root.rglob("*"):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        latest_mtime = max(latest_mtime, stat.st_mtime_ns)
        if path.is_file():
            file_count += 1
    return (latest_mtime, file_count)


def runtime_tokenizer_identity(
    tokenizer_name: str | None = None,
) -> dict[str, str | int]:
    resolved_name = tokenizer_name or current_runtime_tokenizer_name()
    spec = get(resolved_name)
    return {
        "name": spec.name,
        "family": spec.family,
        "version": spec.version,
    }


def _search_index_cache_key(
    root: Path,
) -> tuple[str, tuple[int, int], tuple[int, int], str]:
    resolved_root = root.resolve()
    tokenizer_name = current_runtime_tokenizer_name()
    return (
        str(resolved_root),
        _tree_signature(resolved_root / "normalized"),
        _tree_signature(resolved_root / "compiled"),
        tokenizer_name,
    )


def content_freshness_identity(
    root: Path,
    *,
    tokenizer_name: str | None = None,
) -> dict[str, Any]:
    """Return the current content-derived freshness identity for retrieval data."""
    resolved_root = root.resolve()
    resolved_tokenizer_name = tokenizer_name or current_runtime_tokenizer_name()
    normalized_mtime_ns, normalized_file_count = _tree_signature(
        resolved_root / "normalized"
    )
    compiled_mtime_ns, compiled_file_count = _tree_signature(resolved_root / "compiled")
    return {
        "normalized": {
            "latest_mtime_ns": normalized_mtime_ns,
            "file_count": normalized_file_count,
        },
        "compiled": {
            "latest_mtime_ns": compiled_mtime_ns,
            "file_count": compiled_file_count,
        },
        "tokenizer": runtime_tokenizer_identity(resolved_tokenizer_name),
    }


@lru_cache(maxsize=8)
def _build_search_snapshot_cached(
    cache_key: tuple[str, tuple[int, int], tuple[int, int], str],
) -> RetrievalSnapshot:
    return RetrievalService.from_root(
        Path(cache_key[0]),
        tokenizer=create_tokenizer(cache_key[3]),
    )


def clear_query_search_index_cache() -> None:
    _build_search_snapshot_cached.cache_clear()


def build_retrieval_snapshot(root: Path) -> RetrievalSnapshot:
    _ = validate_runtime_manifest_tokenizer(root)
    return _build_search_snapshot_cached(_search_index_cache_key(root))


def build_search_index(root: Path) -> tuple[RuntimeSearchIndex, int, int]:
    snapshot = build_retrieval_snapshot(root)
    return (snapshot.index, snapshot.records_indexed, snapshot.pages_indexed)


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
