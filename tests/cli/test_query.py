from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.cli.main import app
from snowiki.config import resolve_repo_asset_path
from snowiki.search.workspace import build_retrieval_snapshot


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


def test_query_cache_invalidates_after_ingest(tmp_path: Path) -> None:
    fixture = resolve_repo_asset_path("fixtures/claude/basic.jsonl")
    _ = run_ingest(fixture, source="claude", root=tmp_path)

    first_snapshot = build_retrieval_snapshot(tmp_path)
    first_counts = (first_snapshot.records_indexed, first_snapshot.pages_indexed)

    second_fixture = resolve_repo_asset_path("fixtures/claude/with_tools.jsonl")
    _ = run_ingest(second_fixture, source="claude", root=tmp_path)

    second_snapshot = build_retrieval_snapshot(tmp_path)
    second_counts = (second_snapshot.records_indexed, second_snapshot.pages_indexed)

    assert second_counts[0] > first_counts[0]
    assert second_counts[1] >= first_counts[1]


def test_query_cache_invalidates_after_rebuild(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    _ = run_ingest(claude_basic_fixture, source="claude", root=tmp_path)

    before = build_retrieval_snapshot(tmp_path)
    before_size = before.index.size

    result = run_rebuild(tmp_path)
    after = build_retrieval_snapshot(tmp_path)

    assert result["records_indexed"] == after.records_indexed
    assert result["pages_indexed"] == after.pages_indexed
    assert after.index.size >= before_size
