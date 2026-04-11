from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from snowiki.cli.main import app


def test_rebuild_generates_compiled_outputs_and_index_manifest(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    runner = CliRunner()
    fixture = claude_basic_fixture
    ingest = runner.invoke(
        app,
        ["ingest", str(fixture), "--source", "claude", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    rebuild = runner.invoke(
        app,
        ["rebuild", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert rebuild.exit_code == 0, rebuild.output
    payload = json.loads(rebuild.output)
    assert payload["ok"] is True
    assert (tmp_path / "compiled/overview.md").exists()
    assert (tmp_path / "index/manifest.json").exists()
    assert payload["result"]["compiled_count"] >= 1
