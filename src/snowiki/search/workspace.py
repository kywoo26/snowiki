from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import build_retrieval_snapshot as _build_retrieval_snapshot
from .cache import build_search_index as _build_search_index
from .cache import clear_query_search_index_cache as _clear_query_search_index_cache
from .cache import (
    validate_runtime_manifest_tokenizer as _validate_runtime_manifest_tokenizer,
)
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


def validate_runtime_manifest_tokenizer(root: Path) -> str | None:
    return _validate_runtime_manifest_tokenizer(
        root,
        tokenizer_name=current_runtime_tokenizer_name(),
    )


def clear_query_search_index_cache() -> None:
    _clear_query_search_index_cache()


def build_retrieval_snapshot(root: Path) -> RetrievalSnapshot:
    return _build_retrieval_snapshot(
        root,
        tokenizer_name=current_runtime_tokenizer_name(),
        snapshot_builder=RetrievalService.from_root,
        tokenizer_factory=create_tokenizer,
        tokenizer_spec_getter=get,
    )


def build_search_index(root: Path) -> tuple[RuntimeSearchIndex, int, int]:
    return _build_search_index(
        root,
        tokenizer_name=current_runtime_tokenizer_name(),
        snapshot_builder=RetrievalService.from_root,
        tokenizer_factory=create_tokenizer,
        tokenizer_spec_getter=get,
    )


def load_normalized_records(root: Path) -> list[dict[str, Any]]:
    return _load_normalized_records(root)
