from __future__ import annotations

from snowiki.storage.index_manifest import RetrievalIdentity

from .models import LEXICAL_INDEX_FORMAT_VERSION, SEARCH_DOCUMENT_FORMAT_VERSION
from .registry import default, get
from .retrieval_identity import retrieval_identity_for_tokenizer


def current_runtime_index_formats() -> tuple[str, str]:
    return (SEARCH_DOCUMENT_FORMAT_VERSION, LEXICAL_INDEX_FORMAT_VERSION)


def current_runtime_tokenizer_name() -> str:
    return default().name


def current_runtime_retrieval_identity() -> RetrievalIdentity:
    spec = get(current_runtime_tokenizer_name())
    return RetrievalIdentity(name=spec.name, family=spec.family, version=str(spec.version))


__all__ = [
    "current_runtime_index_formats",
    "current_runtime_retrieval_identity",
    "current_runtime_tokenizer_name",
    "retrieval_identity_for_tokenizer",
]
