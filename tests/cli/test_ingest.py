from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from snowiki.cli.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_ingest_claude_writes_raw_and_normalized_records(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture = ROOT / "fixtures" / "claude" / "basic.jsonl"
    result = runner.invoke(
        app,
        [
            "ingest",
            str(fixture),
            "--source",
            "claude",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["result"]["session_id"] == "claude-basic-session"
    assert (tmp_path / "raw").exists()
    assert (tmp_path / "normalized").exists()
    assert list((tmp_path / "normalized").rglob("*.json"))


def test_ingest_reports_missing_file_with_non_zero_exit_code() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ingest", "missing.jsonl", "--source", "claude", "--output", "json"],
    )
    assert result.exit_code != 0
