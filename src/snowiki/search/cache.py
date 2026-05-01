from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from snowiki.storage.index_manifest import RetrievalIdentity, current_index_identity
from snowiki.storage.zones import StoragePaths

from .protocols import RuntimeSearchIndex
from .registry import SearchTokenizer
from .runtime_service import RetrievalSnapshot

type LayerCacheKey = tuple[int, int, str]
type RetrievalCacheKey = tuple[str, str, str]
type SnapshotCacheKey = tuple[str, LayerCacheKey, LayerCacheKey, RetrievalCacheKey]


class SnapshotBuilder(Protocol):
    def __call__(
        self,
        root: Path,
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot: ...
def _layer_cache_key(
    latest_mtime_ns: int,
    file_count: int,
    content_hash: str,
) -> LayerCacheKey:
    return (latest_mtime_ns, file_count, content_hash)


def _retrieval_cache_key(name: str, family: str, version: str) -> RetrievalCacheKey:
    return (name, family, version)


def snapshot_cache_key(
    root: Path,
    *,
    retrieval_identity: RetrievalIdentity,
) -> SnapshotCacheKey:
    resolved_root = root.resolve()
    identity = current_index_identity(StoragePaths(resolved_root), retrieval_identity)
    return (
        str(resolved_root),
        _layer_cache_key(
            identity.normalized.latest_mtime_ns,
            identity.normalized.file_count,
            identity.normalized.content_hash,
        ),
        _layer_cache_key(
            identity.compiled.latest_mtime_ns,
            identity.compiled.file_count,
            identity.compiled.content_hash,
        ),
        _retrieval_cache_key(
            retrieval_identity.name,
            retrieval_identity.family,
            retrieval_identity.version,
        ),
    )


@lru_cache(maxsize=8)
def _build_search_snapshot_cached(
    cache_key: SnapshotCacheKey,
    snapshot_builder: SnapshotBuilder,
    tokenizer_factory: Callable[[str], SearchTokenizer],
) -> RetrievalSnapshot:
    return snapshot_builder(
        Path(cache_key[0]),
        tokenizer=tokenizer_factory(cache_key[3][0]),
    )


def clear_query_search_index_cache() -> None:
    _build_search_snapshot_cached.cache_clear()


def build_retrieval_snapshot(
    root: Path,
    *,
    retrieval_identity: RetrievalIdentity,
    snapshot_builder: SnapshotBuilder,
    tokenizer_factory: Callable[[str], SearchTokenizer],
) -> RetrievalSnapshot:
    return _build_search_snapshot_cached(
        snapshot_cache_key(
            root,
            retrieval_identity=retrieval_identity,
        ),
        snapshot_builder,
        tokenizer_factory,
    )


def build_search_index(
    root: Path,
    *,
    retrieval_identity: RetrievalIdentity,
    snapshot_builder: SnapshotBuilder,
    tokenizer_factory: Callable[[str], SearchTokenizer],
) -> tuple[RuntimeSearchIndex, int, int]:
    snapshot = build_retrieval_snapshot(
        root,
        retrieval_identity=retrieval_identity,
        snapshot_builder=snapshot_builder,
        tokenizer_factory=tokenizer_factory,
    )
    return (snapshot.index, snapshot.records_indexed, snapshot.pages_indexed)
