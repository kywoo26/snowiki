from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypeVar, cast

from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_bytes,
    atomic_write_json,
    sanitize_segment,
)

BM25_CACHE_SCHEMA_VERSION = 1
BM25_INDEX_FORMAT_VERSION = "bm25s-v1"

_ARTIFACT_FILENAME = "index.bm25cache"
_MANIFEST_FILENAME = "manifest.json"

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BM25CachePaths:
    root: Path
    manifest_path: Path
    artifact_path: Path


@dataclass(frozen=True, slots=True)
class BM25CacheResult[T]:
    value: T
    metadata: dict[str, object]


type BM25ArtifactBuilder[T] = Callable[[], tuple[T, bytes]]
type BM25ArtifactLoader[T] = Callable[[Path], T]


def bm25s_package_version() -> str:
    try:
        return version("bm25s")
    except PackageNotFoundError:
        return "unknown"


def build_bm25_cache_identity(
    *,
    target_name: str,
    corpus_identity: str,
    corpus_hash: str,
    corpus_cap: int | None,
    documents: Sequence[tuple[str, str]],
    tokenizer_name: str,
    tokenizer_config: Mapping[str, object],
    tokenizer_version: int | str,
    bm25_params: Mapping[str, object],
) -> dict[str, object]:
    """Build a strict, stable BM25 benchmark cache identity."""

    ordered_doc_ids = [doc_id for doc_id, _ in documents]
    document_payload = [
        {"content_hash": _sha256_text(content), "doc_id": doc_id}
        for doc_id, content in documents
    ]
    identity: dict[str, object] = {
        "target_name": target_name,
        "corpus": {
            "identity": corpus_identity,
            "hash": corpus_hash,
            "cap": corpus_cap,
        },
        "documents": {
            "ordered_doc_ids": ordered_doc_ids,
            "content_hash": _sha256_json(document_payload),
        },
        "tokenizer": {
            "name": tokenizer_name,
            "config": dict(sorted(tokenizer_config.items())),
            "version": tokenizer_version,
        },
        "bm25": {
            "params": dict(sorted(bm25_params.items())),
            "package_version": bm25s_package_version(),
        },
        "cache_schema_version": BM25_CACHE_SCHEMA_VERSION,
        "index_format_version": BM25_INDEX_FORMAT_VERSION,
    }
    identity["identity_hash"] = _sha256_json(identity)
    return identity


def bm25_cache_paths(
    *,
    storage_paths: StoragePaths,
    target_name: str,
    identity_hash: str,
) -> BM25CachePaths:
    root = (
        storage_paths.index
        / "bench"
        / "bm25"
        / sanitize_segment(target_name)
        / sanitize_segment(identity_hash)
    )
    return BM25CachePaths(
        root=root,
        manifest_path=root / _MANIFEST_FILENAME,
        artifact_path=root / _ARTIFACT_FILENAME,
    )


def load_or_rebuild_bm25_cache[T](
    *,
    storage_paths: StoragePaths,
    identity: Mapping[str, object],
    build_artifact: BM25ArtifactBuilder[T],
    load_artifact: BM25ArtifactLoader[T],
) -> BM25CacheResult[T]:
    """Load a BM25 benchmark artifact or rebuild it on any stale/corrupt state."""

    target_name = _required_str(identity, "target_name")
    identity_hash = _required_str(identity, "identity_hash")
    paths = bm25_cache_paths(
        storage_paths=storage_paths,
        target_name=target_name,
        identity_hash=identity_hash,
    )

    miss_reason = _cache_miss_reason(paths=paths, identity_hash=identity_hash)
    if miss_reason is None:
        try:
            value = load_artifact(paths.artifact_path)
        except Exception:
            miss_reason = "corrupt_load"
        else:
            return BM25CacheResult(
                value=value,
                metadata=_cache_metadata(
                    cache_hit=True,
                    cache_status="hit",
                    cache_miss_reason=None,
                    cache_rebuilt=False,
                    cache_manifest_path=paths.manifest_path,
                    index_build_seconds=0.0,
                ),
            )

    start = time.perf_counter()
    value, artifact_bytes = build_artifact()
    build_seconds = time.perf_counter() - start
    manifest = _manifest_payload(
        identity=identity,
        identity_hash=identity_hash,
        artifact_path=paths.artifact_path,
    )
    try:
        _ = atomic_write_bytes(paths.artifact_path, artifact_bytes)
        _ = atomic_write_json(paths.manifest_path, manifest)
    except OSError:
        return BM25CacheResult(
            value=value,
            metadata=_cache_metadata(
                cache_hit=False,
                cache_status="disabled_or_unwritable",
                cache_miss_reason="unwritable_cache_directory",
                cache_rebuilt=True,
                cache_manifest_path=paths.manifest_path,
                index_build_seconds=build_seconds,
            ),
        )

    return BM25CacheResult(
        value=value,
        metadata=_cache_metadata(
            cache_hit=False,
            cache_status="rebuilt",
            cache_miss_reason=miss_reason,
            cache_rebuilt=True,
            cache_manifest_path=paths.manifest_path,
            index_build_seconds=build_seconds,
        ),
    )


def _cache_miss_reason(*, paths: BM25CachePaths, identity_hash: str) -> str | None:
    if not paths.manifest_path.exists():
        return "missing_manifest"
    try:
        payload = cast(
            object,
            json.loads(paths.manifest_path.read_text(encoding="utf-8")),
        )
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return "malformed_manifest"
    if not isinstance(payload, Mapping):
        return "malformed_manifest"
    manifest = cast(Mapping[str, object], payload)
    if (
        manifest.get("schema_version") != BM25_CACHE_SCHEMA_VERSION
        or manifest.get("identity_hash") != identity_hash
        or manifest.get("index_format_version") != BM25_INDEX_FORMAT_VERSION
    ):
        return "manifest_mismatch"
    if not paths.artifact_path.is_file():
        return "missing_artifact"
    return None


def _manifest_payload(
    *,
    identity: Mapping[str, object],
    identity_hash: str,
    artifact_path: Path,
) -> dict[str, object]:
    return {
        "schema_version": BM25_CACHE_SCHEMA_VERSION,
        "identity_hash": identity_hash,
        "index_format_version": BM25_INDEX_FORMAT_VERSION,
        "identity": dict(identity),
        "artifact_path": artifact_path.name,
    }


def _cache_metadata(
    *,
    cache_hit: bool,
    cache_status: str,
    cache_miss_reason: str | None,
    cache_rebuilt: bool,
    cache_manifest_path: Path,
    index_build_seconds: float,
) -> dict[str, object]:
    return {
        "cache_hit": cache_hit,
        "cache_status": cache_status,
        "cache_miss_reason": cache_miss_reason,
        "cache_rebuilt": cache_rebuilt,
        "cache_manifest_path": cache_manifest_path.as_posix(),
        "cache_schema_version": BM25_CACHE_SCHEMA_VERSION,
        "index_build_seconds": index_build_seconds,
    }


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"BM25 cache identity missing string field: {key}")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
