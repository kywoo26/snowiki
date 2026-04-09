from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from snowiki.cli.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_query_returns_hits_after_cold_start_ingest() -> None:
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

        query = runner.invoke(
            app,
            [
                "query",
                "claude-basic",
                "--mode",
                "lexical",
                "--top-k",
                "3",
                "--output",
                "json",
            ],
            env={"SNOWIKI_ROOT": str(expected_root)},
        )
        assert query.exit_code == 0, query.output
        payload = json.loads(query.output)
        assert payload["ok"] is True
        assert payload["result"]["hits"]
        assert any(
            "claude-basic" in hit["path"] or "claude-basic" in hit["id"]
            for hit in payload["result"]["hits"]
        )
