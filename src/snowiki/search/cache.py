from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from snowiki.search.tokenizer_compat import StaleTokenizerArtifactError
from snowiki.storage.index_manifest import (
    current_index_identity,
    index_manifest_path,
    load_manifest_retrieval_identity,
)
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


class TokenizerSpecLike(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def family(self) -> str: ...

    @property
    def version(self) -> int: ...


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
    tokenizer_name: str,
    tokenizer_spec_getter: Callable[[str], TokenizerSpecLike],
) -> SnapshotCacheKey:
    resolved_root = root.resolve()
    identity = current_index_identity(StoragePaths(resolved_root), tokenizer_name)
    tokenizer_spec = tokenizer_spec_getter(tokenizer_name)
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
            tokenizer_spec.name,
            tokenizer_spec.family,
            str(tokenizer_spec.version),
        ),
    )


def validate_runtime_manifest_tokenizer(
    root: Path,
    *,
    tokenizer_name: str,
) -> str | None:
    paths = StoragePaths(root.resolve())
    current_retrieval_identity = current_index_identity(paths, tokenizer_name).retrieval
    try:
        retrieval_identity = load_manifest_retrieval_identity(paths)
    except (TypeError, ValueError) as error:
        raise StaleTokenizerArtifactError(
            artifact_path=index_manifest_path(paths),
            requested_tokenizer_name=tokenizer_name,
            stored_tokenizer_name=None,
    ) from error
    if retrieval_identity is None:
        return None
    if retrieval_identity != current_retrieval_identity:
        raise StaleTokenizerArtifactError(
            artifact_path=index_manifest_path(paths),
            requested_tokenizer_name=tokenizer_name,
            stored_tokenizer_name=retrieval_identity.name,
        )
    return retrieval_identity.name


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
    tokenizer_name: str,
    snapshot_builder: SnapshotBuilder,
    tokenizer_factory: Callable[[str], SearchTokenizer],
    tokenizer_spec_getter: Callable[[str], TokenizerSpecLike],
) -> RetrievalSnapshot:
    _ = validate_runtime_manifest_tokenizer(root, tokenizer_name=tokenizer_name)
    return _build_search_snapshot_cached(
        snapshot_cache_key(
            root,
            tokenizer_name=tokenizer_name,
            tokenizer_spec_getter=tokenizer_spec_getter,
        ),
        snapshot_builder,
        tokenizer_factory,
    )


def build_search_index(
    root: Path,
    *,
    tokenizer_name: str,
    snapshot_builder: SnapshotBuilder,
    tokenizer_factory: Callable[[str], SearchTokenizer],
    tokenizer_spec_getter: Callable[[str], TokenizerSpecLike],
) -> tuple[RuntimeSearchIndex, int, int]:
    snapshot = build_retrieval_snapshot(
        root,
        tokenizer_name=tokenizer_name,
        snapshot_builder=snapshot_builder,
        tokenizer_factory=tokenizer_factory,
        tokenizer_spec_getter=tokenizer_spec_getter,
    )
    return (snapshot.index, snapshot.records_indexed, snapshot.pages_indexed)
