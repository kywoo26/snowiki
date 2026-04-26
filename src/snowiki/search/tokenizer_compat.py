from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from .registry import default, get, is_tokenizer_compatible


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
        self.details: dict[str, object] = {
            "artifact_path": artifact_path.as_posix(),
            "requested_tokenizer_name": requested_tokenizer_name,
            "stored_tokenizer_name": stored_tokenizer_name,
            "rebuild_required": True,
            "reason": reason,
        }


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
