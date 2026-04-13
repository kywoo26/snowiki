from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.query import run_query
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.cli.main import app
from snowiki.config import resolve_repo_asset_path
from snowiki.search.indexer import SearchDocument, SearchHit
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
    assert payload["command"] == "query"
    assert payload["result"]["query"] == "claude-basic"
    assert payload["result"]["mode"] == "lexical"
    assert payload["result"]["semantic_backend"] is None
    assert payload["result"]["hits"]
    assert any(
        "claude-basic" in hit["path"] or "claude-basic" in hit["id"]
        for hit in payload["result"]["hits"]
    )


def test_query_help_documents_machine_output_flag() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["query", "--help"])

    assert result.exit_code == 0
    assert "--output [human|json]" in result.output
    assert "--top-k INTEGER RANGE" in result.output
    assert "--mode [lexical|hybrid]" in result.output


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


def test_run_query_uses_runtime_snapshot_and_topical_recall_not_benchmark_indexes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    runtime_hit = SearchHit(
        document=SearchDocument(
            id="session-1",
            path="normalized/session-1.json",
            kind="session",
            title="Runtime lexical hit",
            content="runtime lexical content",
            source_type="normalized",
        ),
        score=4.25,
        matched_terms=("runtime", "lexical"),
    )
    snapshot = SimpleNamespace(index=runtime_index, records_indexed=3, pages_indexed=2)

    def fake_build_retrieval_snapshot(root: Path) -> object:
        call_log.append({"fn": "build_retrieval_snapshot", "root": root})
        return snapshot

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {
                "fn": "topical_recall",
                "index": index,
                "query": query,
                "limit": limit,
            }
        )
        return [runtime_hit]

    def fail_bm25(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("query runtime must not promote benchmark BM25 candidates")

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall",
        fake_topical_recall,
    )
    monkeypatch.setattr("snowiki.search.bm25_index.BM25SearchIndex", fail_bm25)

    result = run_query(tmp_path, "runtime lexical", mode="lexical", top_k=4)

    assert result == {
        "query": "runtime lexical",
        "mode": "lexical",
        "semantic_backend": None,
        "records_indexed": 3,
        "pages_indexed": 2,
        "hits": [
            {
                "id": "session-1",
                "path": "normalized/session-1.json",
                "title": "Runtime lexical hit",
                "kind": "session",
                "source_type": "normalized",
                "score": 4.25,
                "matched_terms": ["runtime", "lexical"],
                "summary": "",
            }
        ],
    }
    assert call_log == [
        {"fn": "build_retrieval_snapshot", "root": tmp_path},
        {
            "fn": "topical_recall",
            "index": runtime_index,
            "query": "runtime lexical",
            "limit": 4,
        },
    ]
