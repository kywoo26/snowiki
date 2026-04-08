from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_rebuild_generates_compiled_outputs_and_index_manifest() -> None:
    runner = CliRunner()
    fixture = ROOT / "fixtures" / "claude" / "basic.jsonl"
    with runner.isolated_filesystem():
        ingest = runner.invoke(
            app,
            ["ingest", str(fixture), "--source", "claude", "--output", "json"],
        )
        assert ingest.exit_code == 0, ingest.output

        rebuild = runner.invoke(app, ["rebuild", "--output", "json"])
        assert rebuild.exit_code == 0, rebuild.output
        payload = json.loads(rebuild.output)
        assert payload["ok"] is True
        assert Path("compiled/overview.md").exists()
        assert Path("index/manifest.json").exists()
        assert payload["result"]["compiled_count"] >= 1
