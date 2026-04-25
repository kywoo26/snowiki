from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


def test_prune_sources_dry_run_reports_missing_source_candidates(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    note = source_root / "note.md"
    _ = note.write_text("# Note\n", encoding="utf-8")
    snowiki_root = tmp_path / "snowiki"
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(source_root), "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )
    assert ingest.exit_code == 0, ingest.output
    normalized_path = json.loads(ingest.output)["result"]["documents"][0]["normalized_path"]
    raw_path = json.loads(ingest.output)["result"]["documents"][0]["raw_path"]
    note.unlink()

    result = runner.invoke(
        app,
        ["prune", "sources", "--dry-run", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "prune sources"
    assert payload["result"]["dry_run"] is True
    assert payload["result"]["deleted_count"] == 0
    assert payload["result"]["candidates"] == [
        {
            "kind": "normalized_markdown_record",
            "path": normalized_path,
            "reason": "source_missing",
            "record_id": payload["result"]["candidates"][0]["record_id"],
            "source_path": note.as_posix(),
        },
        {
            "kind": "raw_snapshot",
            "path": raw_path,
            "reason": "unreferenced_after_source_prune",
            "record_id": payload["result"]["candidates"][1]["record_id"],
            "source_path": note.as_posix(),
        },
    ]
    assert (snowiki_root / normalized_path).exists()
    assert (snowiki_root / raw_path).exists()


def test_prune_sources_delete_requires_yes(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["prune", "sources", "--delete", "--all-candidates", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "prune_confirmation_required"
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "normalized").exists()
    assert not (tmp_path / "compiled").exists()


def test_prune_sources_delete_requires_all_candidates(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["prune", "sources", "--delete", "--yes", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "prune_confirmation_required"
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "normalized").exists()
    assert not (tmp_path / "compiled").exists()


def test_prune_sources_delete_removes_candidates_and_rebuilds(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    note = source_root / "note.md"
    _ = note.write_text("# Note\n", encoding="utf-8")
    snowiki_root = tmp_path / "snowiki"
    runner = CliRunner()
    ingest = runner.invoke(
        app,
        ["ingest", str(source_root), "--rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )
    assert ingest.exit_code == 0, ingest.output
    document = json.loads(ingest.output)["result"]["documents"][0]
    note.unlink()

    result = runner.invoke(
        app,
        [
            "prune",
            "sources",
            "--delete",
            "--yes",
            "--all-candidates",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(snowiki_root)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["dry_run"] is False
    assert payload["result"]["deleted_count"] == 2
    assert document["normalized_path"] in payload["result"]["deleted"]
    assert document["raw_path"] in payload["result"]["deleted"]
    assert payload["result"]["tombstone_path"] == "index/source-prune-tombstones.json"
    assert payload["result"]["rebuild"]["compiled_count"] >= 3
    assert not (snowiki_root / document["normalized_path"]).exists()
    assert not (snowiki_root / document["raw_path"]).exists()
    assert (snowiki_root / "compiled" / "index.md").exists()
    assert (snowiki_root / "compiled" / "log.md").exists()
    tombstones = json.loads(
        (snowiki_root / "index" / "source-prune-tombstones.json").read_text(
            encoding="utf-8"
        )
    )
    assert tombstones[-1]["deleted"] == payload["result"]["deleted"]
