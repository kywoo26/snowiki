from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.storage.index_manifest import (
    FreshnessExplanation,
    FreshnessReason,
    IndexIdentity,
    IndexManifest,
    LayerIdentity,
    ManifestRetrievalIdentityMismatchError,
    RetrievalIdentity,
    compare_index_identity,
    current_index_identity,
    current_layer_identity,
    explain_index_freshness,
    index_manifest_path,
    load_index_manifest,
    load_manifest_retrieval_identity,
    normalize_legacy_index_manifest,
    to_status_payload,
    validate_manifest_retrieval_identity,
    validate_retrieval_identity,
    write_index_manifest,
)
from snowiki.storage.zones import StoragePaths


def _layer_payload(content_hash: str) -> dict[str, object]:
    return {
        "latest_mtime_ns": 123,
        "file_count": 2,
        "content_hash": content_hash,
    }


def _manifest_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "records_indexed": 3,
        "pages_indexed": 2,
        "search_documents": 5,
        "compiled_paths": ["compiled/a.md", "compiled/b.md"],
        "identity": {
            "normalized": _layer_payload("normalized-sha256"),
            "compiled": _layer_payload("compiled-sha256"),
            "retrieval": {
                "name": "snowiki-ko",
                "family": "kiwi",
                "version": "1",
            },
            "search_document_format": "1",
            "lexical_index_format": "1",
        },
    }


def _manifest() -> IndexManifest:
    return IndexManifest.from_payload(_manifest_payload())


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(payload), encoding="utf-8")


def test_storage_has_no_search_imports() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "snowiki"
        / "storage"
        / "index_manifest.py"
    ).read_text(encoding="utf-8")

    assert "from snowiki.search" not in source
    assert "import snowiki.search" not in source


def test_index_manifest_roundtrips_through_explicit_payload() -> None:
    payload = _manifest_payload()

    manifest = IndexManifest.from_payload(payload)

    assert manifest.schema_version == 1
    assert manifest.compiled_paths == ("compiled/a.md", "compiled/b.md")
    assert manifest.identity.retrieval.version == "1"
    assert manifest.to_payload() == payload
    assert IndexManifest.from_payload(manifest.to_payload()) == manifest


def test_freshness_explanation_roundtrips_through_explicit_payload() -> None:
    explanation = FreshnessExplanation(
        status="stale",
        reasons=(
            FreshnessReason(
                field_path="identity.compiled.content_hash",
                manifest_value="old",
                current_value="new",
            ),
        ),
        rebuild_required=True,
    )

    payload = explanation.to_payload()

    assert payload == {
        "status": "stale",
        "reasons": [
            {
                "field_path": "identity.compiled.content_hash",
                "manifest_value": "old",
                "current_value": "new",
            }
        ],
        "rebuild_required": True,
    }
    assert FreshnessExplanation.from_payload(payload) == explanation


@pytest.mark.parametrize(
    ("payload", "error_type", "message"),
    [
        ([], TypeError, "IndexManifest must be an object"),
        (
            {
                "schema_version": 1,
                "records_indexed": 3,
                "pages_indexed": 2,
                "search_documents": 5,
                "compiled_paths": ["compiled/a.md"],
            },
            ValueError,
            "identity is required",
        ),
        (
            {
                **_manifest_payload(),
                "compiled_paths": "compiled/a.md",
            },
            TypeError,
            "compiled_paths must be a list of strings",
        ),
        (
            {
                **_manifest_payload(),
                "identity": {
                    "normalized": {
                        **_layer_payload("normalized-sha256"),
                        "latest_mtime_ns": "123",
                    },
                    "compiled": _layer_payload("compiled-sha256"),
                    "retrieval": {
                        "name": "snowiki-ko",
                        "family": "kiwi",
                        "version": "1",
                    },
                },
            },
            TypeError,
            "identity.normalized.latest_mtime_ns must be an integer",
        ),
    ],
)
def test_index_manifest_rejects_invalid_payload_shapes(
    payload: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=message):
        _ = IndexManifest.from_payload(payload)


def test_index_manifest_path_points_to_index_manifest_json(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path)

    assert index_manifest_path(paths) == tmp_path / "index" / "manifest.json"


def test_load_index_manifest_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_index_manifest(StoragePaths(tmp_path)) is None


def test_load_index_manifest_reads_valid_typed_manifest(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path)
    manifest = _manifest()
    _write_json(index_manifest_path(paths), manifest.to_payload())

    assert load_index_manifest(paths) == manifest


def test_load_index_manifest_normalizes_legacy_manifest(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path)
    payload: dict[str, object] = {
        "records_indexed": 3,
        "pages_indexed": 2,
        "search_documents": 5,
        "compiled_paths": ["compiled/a.md"],
        "content_identity": {
            "normalized": _layer_payload("normalized-sha256"),
            "compiled": _layer_payload("compiled-sha256"),
            "tokenizer": {"name": "kiwi_morphology_v1", "family": "kiwi", "version": 2},
        },
        "tokenizer_name": "kiwi_morphology_v1",
    }
    _write_json(index_manifest_path(paths), payload)

    manifest = load_index_manifest(paths)

    assert manifest == normalize_legacy_index_manifest(payload)
    assert manifest is not None
    assert manifest.schema_version == 1
    assert manifest.identity.retrieval == RetrievalIdentity(
        name="kiwi_morphology_v1",
        family="kiwi",
        version="2",
    )


def test_load_manifest_retrieval_identity_reads_legacy_content_identity(
    tmp_path: Path,
) -> None:
    paths = StoragePaths(tmp_path)
    payload: dict[str, object] = {
        "content_identity": {
            "normalized": _layer_payload("normalized-sha256"),
            "compiled": _layer_payload("compiled-sha256"),
            "tokenizer": {
                "name": "kiwi_morphology_v1",
                "family": "kiwi",
                "version": "2",
            },
        }
    }
    _write_json(index_manifest_path(paths), payload)

    assert load_manifest_retrieval_identity(paths) == RetrievalIdentity(
        name="kiwi_morphology_v1",
        family="kiwi",
        version="2",
    )


def test_validate_manifest_retrieval_identity_returns_stored_identity_when_matching(
    tmp_path: Path,
) -> None:
    paths = StoragePaths(tmp_path)
    manifest = _manifest()
    _write_json(index_manifest_path(paths), manifest.to_payload())

    assert validate_manifest_retrieval_identity(paths, manifest.identity.retrieval) == (
        manifest.identity.retrieval
    )


def test_validate_manifest_retrieval_identity_raises_for_family_or_version_mismatch(
    tmp_path: Path,
) -> None:
    paths = StoragePaths(tmp_path)
    manifest = _manifest()
    _write_json(index_manifest_path(paths), manifest.to_payload())

    with pytest.raises(ManifestRetrievalIdentityMismatchError) as excinfo:
        validate_manifest_retrieval_identity(
            paths,
            RetrievalIdentity(
                name=manifest.identity.retrieval.name,
                family=manifest.identity.retrieval.family,
                version="999",
            ),
        )

    assert excinfo.value.actual == manifest.identity.retrieval


def test_normalize_legacy_index_manifest_handles_kiwi_flags() -> None:
    payload: dict[str, object] = {
        "records_indexed": 1,
        "pages_indexed": 1,
        "search_documents": 1,
        "compiled_paths": ["compiled/a.md"],
        "content_identity": {
            "normalized": _layer_payload("normalized-sha256"),
            "compiled": _layer_payload("compiled-sha256"),
        },
        "use_kiwi_tokenizer": True,
        "kiwi_lexical_candidate_mode": "nouns",
    }

    manifest = normalize_legacy_index_manifest(payload)

    assert manifest.identity.retrieval.name == "kiwi_nouns_v1"
    assert manifest.identity.retrieval.family == "kiwi"
    assert manifest.identity.retrieval.version == "2"


def test_write_index_manifest_roundtrips_with_load(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path)
    manifest = _manifest()

    write_index_manifest(paths, manifest)

    assert load_index_manifest(paths) == manifest
    assert json.loads(index_manifest_path(paths).read_text(encoding="utf-8")) == (
        manifest.to_payload()
    )


def test_current_layer_identity_computes_filesystem_signature(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path)
    (paths.normalized / "b.json").parent.mkdir(parents=True, exist_ok=True)
    _ = (paths.normalized / "b.json").write_text("b", encoding="utf-8")
    (paths.normalized / "nested").mkdir()
    _ = (paths.normalized / "nested" / "a.json").write_text("a", encoding="utf-8")

    identity = current_layer_identity(paths, "normalized")

    assert identity.file_count == 2
    assert identity.latest_mtime_ns > 0
    assert identity.content_hash


def test_current_layer_identity_rejects_unknown_layer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="layer must be normalized or compiled"):
        _ = current_layer_identity(StoragePaths(tmp_path), "raw")


def test_current_index_identity_uses_storage_paths_and_explicit_retrieval_identity(
    tmp_path: Path,
) -> None:
    paths = StoragePaths(tmp_path)
    paths.normalized.mkdir(parents=True)
    paths.compiled.mkdir(parents=True)
    retrieval_identity = retrieval_identity_for_tokenizer("regex_v1")

    identity = current_index_identity(paths, retrieval_identity)

    assert identity.normalized == current_layer_identity(paths, "normalized")
    assert identity.compiled == current_layer_identity(paths, "compiled")
    assert identity.retrieval == retrieval_identity
    assert identity.search_document_format == "1"
    assert identity.lexical_index_format == "1"


def test_compare_index_identity_reports_current() -> None:
    manifest = _manifest()

    explanation = compare_index_identity(manifest, manifest.identity)

    assert explanation == FreshnessExplanation(
        status="current",
        reasons=(),
        rebuild_required=False,
    )


def test_compare_index_identity_reports_stale_field_paths() -> None:
    manifest = _manifest()
    current = IndexIdentity(
        normalized=LayerIdentity(
            latest_mtime_ns=999,
            file_count=manifest.identity.normalized.file_count,
            content_hash="changed-normalized",
        ),
        compiled=manifest.identity.compiled,
        retrieval=RetrievalIdentity(name="regex_v1", family="regex", version="1"),
    )

    explanation = compare_index_identity(manifest, current)

    field_paths = {reason.field_path for reason in explanation.reasons}

    assert explanation.status == "stale"
    assert explanation.rebuild_required is True
    assert "identity.normalized.latest_mtime_ns" in field_paths
    assert "identity.normalized.content_hash" in field_paths
    assert "identity.retrieval.name" in field_paths
    assert "identity.retrieval.family" in field_paths


def test_compare_index_identity_reports_format_mismatch() -> None:
    manifest = _manifest()
    current = IndexIdentity(
        normalized=manifest.identity.normalized,
        compiled=manifest.identity.compiled,
        retrieval=manifest.identity.retrieval,
        search_document_format="2",
        lexical_index_format="3",
    )

    explanation = compare_index_identity(manifest, current)

    assert explanation.status == "stale"
    assert explanation.rebuild_required is True
    assert {reason.field_path for reason in explanation.reasons} == {
        "identity.search_document_format",
        "identity.lexical_index_format",
    }


def test_compare_index_identity_reports_missing_manifest() -> None:
    explanation = compare_index_identity(None, _manifest().identity)

    assert explanation.status == "missing"
    assert explanation.rebuild_required is True
    assert explanation.reasons[0].field_path == "identity"


def test_compare_index_identity_reports_invalid_manifest() -> None:
    explanation = compare_index_identity("not-a-manifest", _manifest().identity)

    assert explanation.status == "invalid"
    assert explanation.rebuild_required is True
    assert explanation.reasons[0].field_path == "identity"


def test_explain_index_freshness_returns_invalid_for_bad_manifest_json(
    tmp_path: Path,
) -> None:
    paths = StoragePaths(tmp_path)
    paths.index.mkdir(parents=True, exist_ok=True)
    _ = index_manifest_path(paths).write_text("{", encoding="utf-8")

    manifest, explanation = explain_index_freshness(paths, _manifest().identity)

    assert manifest is None
    assert explanation.status == "invalid"
    assert explanation.rebuild_required is True


def test_tokenizer_version_mismatch_reports_public_path() -> None:
    current = _manifest().identity
    manifest = IndexManifest(
        schema_version=1,
        records_indexed=3,
        pages_indexed=2,
        search_documents=5,
        compiled_paths=("compiled/a.md", "compiled/b.md"),
        identity=IndexIdentity(
            normalized=current.normalized,
            compiled=current.compiled,
            retrieval=RetrievalIdentity(
                name=current.retrieval.name,
                family=current.retrieval.family,
                version="999",
            ),
        ),
    )

    payload = to_status_payload(
        manifest=manifest,
        current=current,
        explanation=compare_index_identity(manifest, current),
        latest_normalized_recorded_at=None,
        latest_compiled_update=None,
    )

    assert set(payload) == {
        "status",
        "manifest_content_identity",
        "current_content_identity",
        "latest_normalized_recorded_at",
        "latest_compiled_update",
        "reasons",
    }
    assert payload["status"] == "stale"
    assert payload["reasons"] == [
        {
            "field_path": "content_identity.tokenizer.version",
            "manifest_value": "999",
            "current_value": 1,
        }
    ]


def test_validate_retrieval_identity_passes_for_expected_name() -> None:
    validate_retrieval_identity(_manifest(), "snowiki-ko")


def test_validate_retrieval_identity_fails_closed_for_mismatch() -> None:
    with pytest.raises(ValueError, match="retrieval identity mismatch"):
        validate_retrieval_identity(_manifest(), "regex_v1")
