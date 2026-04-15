from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from snowiki.cli.main import app
from snowiki.rebuild.integrity import RebuildFreshnessError, verify_rebuild_integrity


def test_verify_rebuild_integrity_restores_compiled_and_index_layers(
    tmp_path: Path,
    claude_basic_fixture: Path,
) -> None:
    runner = CliRunner()

    ingest = runner.invoke(
        app,
        [
            "ingest",
            str(claude_basic_fixture),
            "--source",
            "claude",
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


def test_verify_rebuild_integrity_fails_closed_on_post_rebuild_freshness_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from snowiki.rebuild import integrity

    mismatch_values = iter(
        [
            {
                "normalized": {"latest_mtime_ns": 100, "file_count": 1},
                "compiled": {"latest_mtime_ns": 200, "file_count": 1},
            },
            {
                "normalized": {"latest_mtime_ns": 101, "file_count": 2},
                "compiled": {"latest_mtime_ns": 201, "file_count": 2},
            },
        ]
    )

    monkeypatch.setattr(
        integrity,
        "content_freshness_identity",
        lambda _root: next(mismatch_values),
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
    mismatch_values = iter(
        [
            {
                "normalized": {"latest_mtime_ns": 100, "file_count": 1},
                "compiled": {"latest_mtime_ns": 200, "file_count": 1},
            },
            {
                "normalized": {"latest_mtime_ns": 101, "file_count": 2},
                "compiled": {"latest_mtime_ns": 201, "file_count": 2},
            },
        ]
    )

    monkeypatch.setattr(
        integrity,
        "content_freshness_identity",
        lambda _root: next(mismatch_values),
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
