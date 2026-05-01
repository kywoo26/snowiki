from __future__ import annotations

from pathlib import Path
from typing import Any

from snowiki.storage.index_manifest import (
    ManifestRetrievalIdentityMismatchError,
    RetrievalIdentity,
    index_manifest_path,
    validate_manifest_retrieval_identity,
)
from snowiki.storage.zones import StoragePaths

from .cache import build_retrieval_snapshot as _build_retrieval_snapshot
from .cache import build_search_index as _build_search_index
from .cache import clear_query_search_index_cache as _clear_query_search_index_cache
from .protocols import RuntimeSearchIndex
from .registry import create as create_tokenizer
from .registry import default, get
from .runtime_service import RetrievalService, RetrievalSnapshot
from .runtime_service import load_normalized_records as _load_normalized_records
from .tokenizer_compat import (
    StaleTokenizerArtifactError as _StaleTokenizerArtifactError,
)

StaleTokenizerArtifactError = _StaleTokenizerArtifactError


def current_runtime_tokenizer_name() -> str:
    """Return the canonical tokenizer identity for runtime retrieval."""
    return default().name


def current_runtime_retrieval_identity() -> RetrievalIdentity:
    spec = get(current_runtime_tokenizer_name())
    return RetrievalIdentity(name=spec.name, family=spec.family, version=str(spec.version))


def _validate_runtime_manifest_retrieval_identity(
    root: Path,
    retrieval_identity: RetrievalIdentity,
) -> RetrievalIdentity | None:
    paths = StoragePaths(root.resolve())
    try:
        return validate_manifest_retrieval_identity(
            paths,
            retrieval_identity,
        )
    except ManifestRetrievalIdentityMismatchError as error:
        raise StaleTokenizerArtifactError(
            artifact_path=index_manifest_path(paths),
            requested_tokenizer_name=retrieval_identity.name,
            stored_tokenizer_name=error.actual.name,
        ) from error
    except (TypeError, ValueError) as error:
        raise StaleTokenizerArtifactError(
            artifact_path=index_manifest_path(paths),
            requested_tokenizer_name=retrieval_identity.name,
            stored_tokenizer_name=None,
        ) from error


def validate_runtime_manifest_tokenizer(root: Path) -> str | None:
    retrieval_identity = current_runtime_retrieval_identity()
    stored_retrieval_identity = _validate_runtime_manifest_retrieval_identity(
        root,
        retrieval_identity,
    )
    if stored_retrieval_identity is None:
        return None
    return stored_retrieval_identity.name


def clear_query_search_index_cache() -> None:
    _clear_query_search_index_cache()


def build_retrieval_snapshot(root: Path) -> RetrievalSnapshot:
    retrieval_identity = current_runtime_retrieval_identity()
    _ = _validate_runtime_manifest_retrieval_identity(root, retrieval_identity)
    return _build_retrieval_snapshot(
        root,
        retrieval_identity=retrieval_identity,
        snapshot_builder=RetrievalService.from_root,
        tokenizer_factory=create_tokenizer,
    )


def build_search_index(root: Path) -> tuple[RuntimeSearchIndex, int, int]:
    retrieval_identity = current_runtime_retrieval_identity()
    _ = _validate_runtime_manifest_retrieval_identity(root, retrieval_identity)
    return _build_search_index(
        root,
        retrieval_identity=retrieval_identity,
        snapshot_builder=RetrievalService.from_root,
        tokenizer_factory=create_tokenizer,
    )


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    return _load_normalized_records(root)
