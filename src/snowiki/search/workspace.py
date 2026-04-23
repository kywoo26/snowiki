from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection

from .index_lexical import LexicalIndex, build_lexical_index
from .index_wiki import WikiIndex, build_wiki_index
from .indexer import InvertedIndex, build_blended_index
from .registry import (
    SearchTokenizer,
    default,
    get,
    is_tokenizer_compatible,
)
from .registry import create as create_tokenizer


class StaleTokenizerArtifactError(RuntimeError):
    """Raised when stored tokenizer metadata is missing or incompatible."""

    def __init__(
        self,
        *,
        artifact_path: Path,
        requested_tokenizer_name: str,
        stored_tokenizer_name: str | None,
    ) -> None:
        reason = (
            "missing tokenizer identity"
            if stored_tokenizer_name is None
            else "tokenizer identity mismatch"
        )
        super().__init__(
            f"{artifact_path.as_posix()} is stale: {reason}; rebuild required"
        )
        self.details = {
            "artifact_path": artifact_path.as_posix(),
            "requested_tokenizer_name": requested_tokenizer_name,
            "stored_tokenizer_name": stored_tokenizer_name,
            "rebuild_required": True,
            "reason": reason,
        }


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
    lexical: LexicalIndex
    wiki: WikiIndex
    index: InvertedIndex
    records_indexed: int
    pages_indexed: int


def current_runtime_tokenizer_name() -> str:
    """Return the canonical tokenizer identity for runtime retrieval."""
    return default().name


def normalize_stored_tokenizer_name(metadata: Mapping[str, object]) -> str | None:
    """Normalize canonical or legacy tokenizer metadata to one stable identity."""
    raw_tokenizer_name = metadata.get("tokenizer_name")
    if isinstance(raw_tokenizer_name, str) and raw_tokenizer_name.strip():
        name = raw_tokenizer_name.strip()
        try:
            return get(name).name
        except KeyError:
            return None

    has_legacy_flags = (
        "use_kiwi_tokenizer" in metadata or "kiwi_lexical_candidate_mode" in metadata
    )
    if not has_legacy_flags:
        return None

    raw_use_kiwi_tokenizer = metadata.get("use_kiwi_tokenizer")
    raw_kiwi_lexical_candidate_mode = metadata.get("kiwi_lexical_candidate_mode")
    use_kiwi_tokenizer: bool | None
    if isinstance(raw_use_kiwi_tokenizer, bool):
        use_kiwi_tokenizer = raw_use_kiwi_tokenizer
    elif isinstance(raw_kiwi_lexical_candidate_mode, str):
        use_kiwi_tokenizer = True
    else:
        use_kiwi_tokenizer = None
    if use_kiwi_tokenizer is False:
        return default().name
    if use_kiwi_tokenizer is True:
        if raw_kiwi_lexical_candidate_mode == "nouns":
            return "kiwi_nouns_v1"
        return "kiwi_morphology_v1"
    return default().name


def require_tokenizer_compatibility(
    *,
    artifact_path: Path,
    requested_tokenizer_name: str,
    metadata: Mapping[str, object],
) -> str:
    """Validate stored tokenizer metadata against the requested identity."""
    stored_tokenizer_name = normalize_stored_tokenizer_name(metadata)
    if not is_tokenizer_compatible(stored_tokenizer_name, requested_tokenizer_name):
        raise StaleTokenizerArtifactError(
            artifact_path=artifact_path,
            requested_tokenizer_name=requested_tokenizer_name,
            stored_tokenizer_name=stored_tokenizer_name,
        )
    return cast(str, stored_tokenizer_name)


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
        lexical = (
            build_lexical_index(normalized_records)
            if tokenizer is None
            else build_lexical_index(normalized_records, tokenizer=resolved_tokenizer)
        )
        wiki = (
            build_wiki_index(normalized_pages)
            if tokenizer is None
            else build_wiki_index(normalized_pages, tokenizer=resolved_tokenizer)
        )
        return RetrievalSnapshot(
            lexical=lexical,
            wiki=wiki,
            index=(
                build_blended_index(lexical.documents, wiki.documents)
                if tokenizer is None
                else build_blended_index(
                    lexical.documents,
                    wiki.documents,
                    tokenizer=resolved_tokenizer,
                )
            ),
            records_indexed=len(lexical.documents),
            pages_indexed=len(wiki.documents),
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


def build_search_index(root: Path) -> tuple[InvertedIndex, int, int]:
    snapshot = build_retrieval_snapshot(root)
    return (snapshot.index, snapshot.records_indexed, snapshot.pages_indexed)


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
