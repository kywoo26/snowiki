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
        expected_root = Path.cwd() / ".snowiki"
        ingest = runner.invoke(
            app,
            ["ingest", str(fixture), "--source", "claude", "--output", "json"],
            env={"SNOWIKI_ROOT": str(expected_root)},
        )
        assert ingest.exit_code == 0, ingest.output

        rebuild = runner.invoke(
            app,
            ["rebuild", "--output", "json"],
            env={"SNOWIKI_ROOT": str(expected_root)},
        )
        assert rebuild.exit_code == 0, rebuild.output
        payload = json.loads(rebuild.output)
        assert payload["ok"] is True
        assert (expected_root / "compiled/overview.md").exists()
        assert (expected_root / "index/manifest.json").exists()
        assert payload["result"]["compiled_count"] >= 1
