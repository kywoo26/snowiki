from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import (
    build_retrieval_snapshot as _build_retrieval_snapshot,
)
from .cache import (
    build_search_index as _build_search_index,
)
from .cache import (
    clear_query_search_index_cache as _clear_query_search_index_cache,
)
from .protocols import RuntimeSearchIndex
from .registry import create as create_tokenizer
from .runtime_identity import current_runtime_retrieval_identity
from .runtime_manifest import _validate_runtime_manifest_retrieval_identity
from .runtime_service import RetrievalService, RetrievalSnapshot
from .runtime_service import load_normalized_records as _load_normalized_records


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


__all__ = [
    "build_retrieval_snapshot",
    "build_search_index",
    "clear_query_search_index_cache",
    "load_normalized_records",
]
