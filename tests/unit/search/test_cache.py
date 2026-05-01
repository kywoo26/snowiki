from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.search.cache import snapshot_cache_key
from snowiki.search.models import (
    LEXICAL_INDEX_FORMAT_VERSION,
    SEARCH_DOCUMENT_FORMAT_VERSION,
)
from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.tokenizer_compat import StaleTokenizerArtifactError
from snowiki.search.workspace import validate_runtime_manifest_tokenizer


def test_snapshot_cache_key_uses_stringified_tokenizer_version(tmp_path: Path) -> None:
    cache_key = snapshot_cache_key(
        tmp_path,
        retrieval_identity=retrieval_identity_for_tokenizer("kiwi_morphology_v1"),
    )

    assert cache_key[3] == ("kiwi_morphology_v1", "kiwi", "2")
    assert cache_key[4] == (
        SEARCH_DOCUMENT_FORMAT_VERSION,
        LEXICAL_INDEX_FORMAT_VERSION,
    )


def test_validate_runtime_manifest_tokenizer_rejects_same_name_wrong_version(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "index" / "manifest.json"
    _ = manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _ = manifest_path.write_text(
        json.dumps(
            {
                "content_identity": {
                    "normalized": {
                        "latest_mtime_ns": 0,
                        "file_count": 0,
                        "content_hash": "",
                    },
                    "compiled": {
                        "latest_mtime_ns": 0,
                        "file_count": 0,
                        "content_hash": "",
                    },
                    "tokenizer": {
                        "name": "kiwi_morphology_v1",
                        "family": "kiwi",
                        "version": "1",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StaleTokenizerArtifactError, match="rebuild required"):
        _ = validate_runtime_manifest_tokenizer(tmp_path)
