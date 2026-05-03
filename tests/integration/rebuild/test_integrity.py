from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from tests.helpers.markdown_ingest import write_markdown_source

from snowiki.cli.main import app
from snowiki.rebuild.integrity import RebuildFreshnessError, verify_rebuild_integrity
from snowiki.search.workspace import (
    StaleTokenizerArtifactError,
    build_retrieval_snapshot,
    current_runtime_index_formats,
    current_runtime_tokenizer_name,
)
from snowiki.storage.index_manifest import (
    IndexIdentity,
    LayerIdentity,
    RetrievalIdentity,
)


def _identity(latest_mtime_ns: int, file_count: int) -> IndexIdentity:
    search_document_format, lexical_index_format = current_runtime_index_formats()
    return IndexIdentity(
        normalized=LayerIdentity(
            latest_mtime_ns=latest_mtime_ns,
            file_count=file_count,
            content_hash=f"normalized-{latest_mtime_ns}",
        ),
        compiled=LayerIdentity(
            latest_mtime_ns=latest_mtime_ns + 100,
            file_count=file_count,
            content_hash=f"compiled-{latest_mtime_ns}",
        ),
        retrieval=RetrievalIdentity(
            name=current_runtime_tokenizer_name(),
            family="kiwi",
            version="2",
        ),
        search_document_format=search_document_format,
        lexical_index_format=lexical_index_format,
    )


def test_verify_rebuild_integrity_restores_compiled_and_index_layers(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    source_path = write_markdown_source(tmp_path)

    ingest = runner.invoke(
        app,
        [
            "ingest",
            str(source_path),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    initial_rebuild = runner.invoke(
        app, ["rebuild", "--output", "json"], env={"SNOWIKI_ROOT": str(tmp_path)}
    )
    assert initial_rebuild.exit_code == 0, initial_rebuild.output
    before_paths = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "compiled").rglob("*.md")
    )
    assert before_paths

    result = verify_rebuild_integrity(tmp_path)

    assert result["compiled_before"] == before_paths
    assert result["compiled_after"] == before_paths
    assert result["compiled_restored"] is True
    assert result["index_restored"] is True
    assert result["content_identity"] == result["current_content_identity"]
    assert result["freshness_restored"] is True
    manifest = json.loads(
        (tmp_path / "index" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["identity"]["retrieval"]["name"] == current_runtime_tokenizer_name()


def test_verify_rebuild_integrity_fails_closed_on_post_rebuild_freshness_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from snowiki.rebuild import integrity

    mismatch_values = iter([_identity(100, 1), _identity(101, 2)])

    monkeypatch.setattr(
        integrity,
        "current_index_identity",
        lambda _paths, _tokenizer_name, **_kwargs: next(mismatch_values),
    )
    monkeypatch.setattr(
        integrity.CompilerEngine,
        "rebuild",
        lambda self: ["compiled/overview.md"],
    )
    monkeypatch.setattr(
        integrity,
        "build_retrieval_snapshot",
        lambda _root: type(
            "Snapshot",
            (),
            {
                "records_indexed": 1,
                "pages_indexed": 1,
                "index": type("Index", (), {"size": 2})(),
            },
        )(),
    )
    manifest_path = tmp_path / "index" / "manifest.json"

    with pytest.raises(RebuildFreshnessError) as excinfo:
        verify_rebuild_integrity(tmp_path)

    assert (
        excinfo.value.result["content_identity"]
        != excinfo.value.result["current_content_identity"]
    )
    assert manifest_path.exists() is False


def test_run_rebuild_with_integrity_does_not_overwrite_existing_manifest_on_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from snowiki.rebuild import integrity

    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"published": "previous"}', encoding="utf-8")
    mismatch_values = iter([_identity(100, 1), _identity(101, 2)])

    monkeypatch.setattr(
        integrity,
        "current_index_identity",
        lambda _paths, _tokenizer_name, **_kwargs: next(mismatch_values),
    )
    monkeypatch.setattr(
        integrity.CompilerEngine,
        "rebuild",
        lambda self: ["compiled/overview.md"],
    )
    monkeypatch.setattr(
        integrity,
        "build_retrieval_snapshot",
        lambda _root: type(
            "Snapshot",
            (),
            {
                "records_indexed": 1,
                "pages_indexed": 1,
                "index": type("Index", (), {"size": 2})(),
            },
        )(),
    )

    with pytest.raises(RebuildFreshnessError):
        integrity.run_rebuild_with_integrity(tmp_path)

    assert manifest_path.read_text(encoding="utf-8") == '{"published": "previous"}'


def test_build_retrieval_snapshot_fails_closed_when_manifest_tokenizer_identity_missing(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
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
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        StaleTokenizerArtifactError, match="rebuild required"
    ) as excinfo:
        build_retrieval_snapshot(tmp_path)

    assert excinfo.value.details == {
        "artifact_path": manifest_path.as_posix(),
        "requested_tokenizer_name": current_runtime_tokenizer_name(),
        "stored_tokenizer_name": None,
        "rebuild_required": True,
        "reason": "missing tokenizer identity",
    }


def test_build_retrieval_snapshot_fails_closed_when_manifest_tokenizer_identity_mismatches(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
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
                        "name": "kiwi_nouns_v1",
                        "family": "kiwi",
                        "version": "1",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        StaleTokenizerArtifactError, match="rebuild required"
    ) as excinfo:
        build_retrieval_snapshot(tmp_path)

    assert excinfo.value.details == {
        "artifact_path": manifest_path.as_posix(),
        "requested_tokenizer_name": current_runtime_tokenizer_name(),
        "stored_tokenizer_name": "kiwi_nouns_v1",
        "rebuild_required": True,
        "reason": "tokenizer identity mismatch",
    }
