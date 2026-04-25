from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


def test_ingest_markdown_file_writes_raw_and_normalized_records(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    _ = note.write_text(
        """---
title: Test Note
tags:
  - ingest
---
# Test Note

Markdown body.
""",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ingest",
            str(note),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["result"]["source_root"] == tmp_path.as_posix()
    assert payload["result"]["documents_seen"] == 1
    assert payload["result"]["documents_inserted"] == 1
    assert payload["result"]["documents_updated"] == 0
    assert payload["result"]["documents_unchanged"] == 0
    assert payload["result"]["documents_stale"] == 0
    assert payload["result"]["rebuild_required"] is True
    assert payload["result"]["documents"][0]["relative_path"] == "note.md"
    assert (tmp_path / "snowiki" / "raw" / "markdown").exists()
    assert list((tmp_path / "snowiki" / "normalized" / "markdown").rglob("*.json"))


def test_ingest_markdown_directory_recurses_and_rebuilds(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    nested = docs / "nested"
    nested.mkdir(parents=True)
    _ = (docs / "README.md").write_text("# Readme", encoding="utf-8")
    _ = (nested / "guide.markdown").write_text("# Guide", encoding="utf-8")
    _ = (docs / "ignore.txt").write_text("ignore", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ingest", str(docs), "--rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["documents_seen"] == 2
    assert payload["result"]["rebuild_required"] is False
    assert payload["result"]["rebuild"]["compiled_count"] >= 2
    assert (tmp_path / "snowiki" / "compiled" / "summaries").exists()


def test_ingest_markdown_uses_explicit_source_root(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    docs = vault / "docs"
    docs.mkdir(parents=True)
    note = docs / "note.md"
    _ = note.write_text("# Note", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ingest",
            str(note),
            "--source-root",
            str(vault),
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["source_root"] == vault.resolve().as_posix()
    assert payload["result"]["documents"][0]["relative_path"] == "docs/note.md"


def test_ingest_help_has_no_legacy_source_option() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0, result.output
    assert "--source-root" in result.output
    assert "--source " not in result.output


def test_ingest_markdown_reports_unchanged_on_second_run(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    _ = note.write_text("# Note", encoding="utf-8")
    runner = CliRunner()

    first = runner.invoke(
        app,
        ["ingest", str(note), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )
    second = runner.invoke(
        app,
        ["ingest", str(note), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    payload = json.loads(second.output)
    assert payload["result"]["documents_inserted"] == 0
    assert payload["result"]["documents_updated"] == 0
    assert payload["result"]["documents_unchanged"] == 1


def test_ingest_reports_operation_local_stale_documents(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    note = docs / "note.md"
    extra = docs / "extra.md"
    stale = docs / "stale.md"
    _ = note.write_text("# Note", encoding="utf-8")
    _ = stale.write_text("# Stale", encoding="utf-8")
    runner = CliRunner()

    first = runner.invoke(
        app,
        ["ingest", str(docs), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )
    assert first.exit_code == 0, first.output
    _ = stale.write_text("# Stale\n\nChanged.", encoding="utf-8")
    _ = extra.write_text("# Extra", encoding="utf-8")

    second = runner.invoke(
        app,
        ["ingest", str(note), "--source-root", str(docs), "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path / "snowiki")},
    )

    assert second.exit_code == 0, second.output
    payload = json.loads(second.output)
    assert payload["result"]["documents_seen"] == 1
    assert payload["result"]["documents_stale"] == 1


def test_ingest_reports_missing_file_with_non_zero_exit_code() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ingest", "missing.md", "--output", "json"],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "ingest_failed"


def test_ingest_reports_non_markdown_single_file(tmp_path: Path) -> None:
    note = tmp_path / "note.txt"
    _ = note.write_text("not markdown", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["ingest", str(note), "--output", "json"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["error"]["code"] == "ingest_failed"
    assert "expected a Markdown file" in payload["error"]["message"]


def test_ingest_reports_privacy_blocked_for_sensitive_path(tmp_path: Path) -> None:
    secret = tmp_path / ".env"
    _ = secret.write_text("SECRET=value", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["ingest", str(secret), "--output", "json"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["error"]["code"] == "privacy_blocked"
