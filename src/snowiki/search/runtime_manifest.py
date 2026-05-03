from __future__ import annotations

from pathlib import Path

from snowiki.storage.index_manifest import (
    ManifestRetrievalIdentityMismatchError,
    RetrievalIdentity,
    index_manifest_path,
    validate_manifest_retrieval_identity,
)
from snowiki.storage.zones import StoragePaths

from .tokenizer_compat import StaleTokenizerArtifactError


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
    from .runtime_identity import current_runtime_retrieval_identity

    retrieval_identity = current_runtime_retrieval_identity()
    stored_retrieval_identity = _validate_runtime_manifest_retrieval_identity(
        root,
        retrieval_identity,
    )
    if stored_retrieval_identity is None:
        return None
    return stored_retrieval_identity.name


__all__ = [
    "_validate_runtime_manifest_retrieval_identity",
    "validate_runtime_manifest_tokenizer",
]
