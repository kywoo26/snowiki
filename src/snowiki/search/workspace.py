from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection
from snowiki.config import (
    normalize_runtime_lexical_policy,
    resolve_runtime_lexical_policy,
)
from snowiki.storage.zones import read_json, relative_to_root_or_posix

from .index_lexical import LexicalIndex, build_lexical_index
from .index_wiki import WikiIndex, build_wiki_index
from .indexer import InvertedIndex, build_blended_index

RUNTIME_LEXICAL_POLICY_VERSION = 1


class RuntimeLexicalPolicyMismatchError(RuntimeError):
    """Raised when stored index policy metadata disagrees with runtime policy."""


def runtime_lexical_policy_identity(
    lexical_policy: str | None = None,
) -> dict[str, str | int]:
    """Return the normalized runtime lexical policy identity."""

    effective_policy = (
        normalize_runtime_lexical_policy(lexical_policy)
        if lexical_policy is not None
        else resolve_runtime_lexical_policy()
    )
    return {
        "lexical_policy": effective_policy,
        "lexical_policy_version": RUNTIME_LEXICAL_POLICY_VERSION,
    }


def _index_manifest_path(root: Path) -> Path:
    return root.resolve() / "index" / "manifest.json"


def ensure_runtime_policy_compatible(
    root: Path, *, lexical_policy: str | None = None
) -> dict[str, str | int]:
    """Require stored index metadata to match the active runtime policy."""

    runtime_identity = runtime_lexical_policy_identity(lexical_policy)
    manifest_path = _index_manifest_path(root)
    if not manifest_path.exists():
        return runtime_identity

    manifest_payload = read_json(manifest_path, None)
    manifest_display_path = relative_to_root_or_posix(root.resolve(), manifest_path)
    if not isinstance(manifest_payload, dict):
        raise RuntimeLexicalPolicyMismatchError(
            f"index manifest '{manifest_display_path}' is unreadable; run `snowiki rebuild` "
            f"for runtime lexical policy '{runtime_identity['lexical_policy']}'"
        )

    stored_policy = manifest_payload.get("lexical_policy")
    stored_version = manifest_payload.get("lexical_policy_version")
    if not isinstance(stored_policy, str) or not isinstance(stored_version, int):
        raise RuntimeLexicalPolicyMismatchError(
            f"index manifest '{manifest_display_path}' is missing runtime lexical policy "
            "metadata; run `snowiki rebuild` before querying under a runtime policy"
        )

    try:
        normalized_stored_policy = normalize_runtime_lexical_policy(stored_policy)
    except ValueError as exc:
        raise RuntimeLexicalPolicyMismatchError(
            f"index manifest '{manifest_display_path}' records unsupported runtime lexical "
            f"policy '{stored_policy}'; run `snowiki rebuild`"
        ) from exc

    stored_identity = {
        "lexical_policy": normalized_stored_policy,
        "lexical_policy_version": stored_version,
    }
    if stored_identity != runtime_identity:
        raise RuntimeLexicalPolicyMismatchError(
            "runtime lexical policy does not match stored index metadata: "
            f"runtime={runtime_identity['lexical_policy']}@"
            f"v{runtime_identity['lexical_policy_version']}, "
            f"stored={stored_identity['lexical_policy']}@"
            f"v{stored_identity['lexical_policy_version']} in '{manifest_display_path}'; "
            "run `snowiki rebuild` to refresh the index explicitly"
        )
    return runtime_identity


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
    lexical_policy: str
    lexical_policy_version: int
    lexical: LexicalIndex
    wiki: WikiIndex
    index: InvertedIndex
    records_indexed: int
    pages_indexed: int


class RetrievalService:
    """Canonical retrieval assembly service."""

    @classmethod
    def from_root(
        cls, root: Path, *, lexical_policy: str | None = None
    ) -> RetrievalSnapshot:
        runtime_identity = ensure_runtime_policy_compatible(
            root, lexical_policy=lexical_policy
        )
        effective_policy = cast(str, runtime_identity["lexical_policy"])
        compiler = CompilerEngine(root)
        records = compiler.load_normalized_records()
        pages = compiler.build_pages(records) if records else []
        return cls.from_records_and_pages(
            records=records,
            pages=pages,
            lexical_policy=effective_policy,
        )

    @classmethod
    def from_records_and_pages(
        cls,
        *,
        records: list[NormalizedRecord] | list[dict[str, Any]],
        pages: list[CompiledPage] | list[dict[str, object]],
        lexical_policy: str | None = None,
    ) -> RetrievalSnapshot:
        runtime_identity = runtime_lexical_policy_identity(lexical_policy)
        effective_policy = cast(str, runtime_identity["lexical_policy"])
        lexical = build_lexical_index(
            cls._normalize_records(records), lexical_policy=effective_policy
        )
        wiki = build_wiki_index(
            cls._normalize_pages(pages), lexical_policy=effective_policy
        )
        return RetrievalSnapshot(
            lexical_policy=effective_policy,
            lexical_policy_version=cast(
                int, runtime_identity["lexical_policy_version"]
            ),
            lexical=lexical,
            wiki=wiki,
            index=build_blended_index(
                lexical.documents,
                wiki.documents,
                lexical_policy=effective_policy,
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


def _search_index_cache_key(
    root: Path, lexical_policy: str | None = None
) -> tuple[str, str, int, tuple[int, int], tuple[int, int]]:
    resolved_root = root.resolve()
    runtime_identity = runtime_lexical_policy_identity(lexical_policy)
    return (
        str(resolved_root),
        cast(str, runtime_identity["lexical_policy"]),
        cast(int, runtime_identity["lexical_policy_version"]),
        _tree_signature(resolved_root / "normalized"),
        _tree_signature(resolved_root / "compiled"),
    )


def content_freshness_identity(root: Path) -> dict[str, dict[str, int]]:
    """Return the current content-derived freshness identity for retrieval data."""
    resolved_root = root.resolve()
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
    }


@lru_cache(maxsize=8)
def _build_search_snapshot_cached(
    cache_key: tuple[str, str, int, tuple[int, int], tuple[int, int]],
) -> RetrievalSnapshot:
    return RetrievalService.from_root(Path(cache_key[0]), lexical_policy=cache_key[1])


def clear_query_search_index_cache() -> None:
    _build_search_snapshot_cached.cache_clear()


def build_retrieval_snapshot(
    root: Path, *, lexical_policy: str | None = None
) -> RetrievalSnapshot:
    return _build_search_snapshot_cached(_search_index_cache_key(root, lexical_policy))


def build_search_index(
    root: Path, *, lexical_policy: str | None = None
) -> tuple[InvertedIndex, int, int]:
    snapshot = build_retrieval_snapshot(root, lexical_policy=lexical_policy)
    return (snapshot.index, snapshot.records_indexed, snapshot.pages_indexed)


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    compiler = CompilerEngine(root)
    return [
        normalized_record_to_search_mapping(record)
        for record in compiler.load_normalized_records()
    ]
