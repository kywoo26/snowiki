from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from snowiki.cli.main import app


def test_query_returns_hits_after_cold_start_ingest(
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
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert query.exit_code == 0, query.output
    payload = json.loads(query.output)
    assert payload["ok"] is True
    assert payload["result"]["hits"]
    assert any(
        "claude-basic" in hit["path"] or "claude-basic" in hit["id"]
        for hit in payload["result"]["hits"]
    )
