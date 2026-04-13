from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.query import run_query
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.cli.commands.recall import run_recall
from snowiki.cli.main import app
from snowiki.config import resolve_repo_asset_path
from snowiki.search.indexer import SearchDocument, SearchHit
from snowiki.search.workspace import (
    RuntimeLexicalPolicyMismatchError,
    build_retrieval_snapshot,
    clear_query_search_index_cache,
)


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
    assert "--lexical-policy [legacy-lexical|korean-mixed-lexical]" in result.output
    assert "--mode [lexical|hybrid]" in result.output


def test_recall_json_routes_temporal_queries_and_freezes_payload_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    call_log: list[dict[str, object]] = []
    hit = SearchHit(
        document=SearchDocument(
            id="session-yesterday",
            path="sessions/yesterday.json",
            kind="session",
            title="Yesterday session",
            content="temporal recall content",
            summary="Temporal recall hit.",
            source_type="normalized",
        ),
        score=9.87654321,
        matched_terms=("yesterday", "recall"),
    )

    def fake_from_root(root: Path, *, lexical_policy: str | None = None) -> object:
        call_log.append(
            {"fn": "from_root", "root": root, "lexical_policy": lexical_policy}
        )
        return SimpleNamespace(index=object(), lexical_policy=lexical_policy)

    def fail_known_item_lookup(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError(
            "recall should route temporal queries away from known-item"
        )

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("recall should not fall back to topical search here")

    def fake_temporal_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "temporal_recall", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.recall.RetrievalService.from_root", fake_from_root
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.known_item_lookup", fail_known_item_lookup
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.topical_recall", fail_topical_recall
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.temporal_recall", fake_temporal_recall
    )

    result = runner.invoke(
        app,
        ["recall", "yesterday", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "command": "recall",
        "ok": True,
        "result": {
            "hits": [
                {
                    "id": "session-yesterday",
                    "kind": "session",
                    "path": "sessions/yesterday.json",
                    "score": 9.876543,
                    "summary": "Temporal recall hit.",
                    "title": "Yesterday session",
                }
            ],
            "lexical_policy": "legacy-lexical",
            "lexical_policy_source": "default",
            "strategy": "temporal",
            "target": "yesterday",
        },
    }
    assert call_log == [
        {"fn": "from_root", "root": tmp_path, "lexical_policy": "legacy-lexical"},
        {
            "fn": "temporal_recall",
            "index": call_log[1]["index"],
            "query": "yesterday",
            "limit": 10,
        },
    ]


def test_recall_json_accepts_iso_date_input_against_runtime_fixture(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    runner = CliRunner()

    ingest = runner.invoke(
        app,
        ["ingest", str(claude_basic_fixture), "--source", "claude", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )
    assert ingest.exit_code == 0, ingest.output

    result = runner.invoke(
        app,
        ["recall", "2026-04-01", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "recall"
    assert payload["result"]["target"] == "2026-04-01"
    assert payload["result"]["strategy"] == "date"
    assert payload["result"]["hits"]
    assert any(
        "normalized/claude/2026/04/01/" in hit["path"]
        for hit in payload["result"]["hits"]
    )


def test_run_recall_prefers_known_item_before_topic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    hit = SearchHit(
        document=SearchDocument(
            id="session-known-item",
            path="normalized/session-known-item.json",
            kind="session",
            title="Known item hit",
            content="known item content",
            summary="Known item summary.",
            source_type="normalized",
        ),
        score=3.5,
        matched_terms=("known", "item"),
    )

    def fake_from_root(root: Path, *, lexical_policy: str | None = None) -> object:
        call_log.append(
            {"fn": "from_root", "root": root, "lexical_policy": lexical_policy}
        )
        return SimpleNamespace(index=runtime_index, lexical_policy=lexical_policy)

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "known_item_lookup", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("known-item hits should prevent topical fallback")

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("known-item queries should not use temporal recall")

    monkeypatch.setattr(
        "snowiki.cli.commands.recall.RetrievalService.from_root", fake_from_root
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.known_item_lookup", fake_known_item_lookup
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.topical_recall", fail_topical_recall
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.temporal_recall", fail_temporal_recall
    )

    result = run_recall(tmp_path, "known item")

    assert result == {
        "target": "known item",
        "strategy": "known_item",
        "lexical_policy": "legacy-lexical",
        "lexical_policy_source": "default",
        "hits": [
            {
                "id": "session-known-item",
                "path": "normalized/session-known-item.json",
                "title": "Known item hit",
                "kind": "session",
                "score": 3.5,
                "summary": "Known item summary.",
            }
        ],
    }
    assert call_log == [
        {"fn": "from_root", "root": tmp_path, "lexical_policy": "legacy-lexical"},
        {
            "fn": "known_item_lookup",
            "index": runtime_index,
            "query": "known item",
            "limit": 10,
        },
    ]


def test_run_recall_routes_iso_dates_to_date_window_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_log: list[dict[str, object]] = []
    hit = SearchHit(
        document=SearchDocument(
            id="session-date-window",
            path="normalized/session-date-window.json",
            kind="session",
            title="Date window hit",
            content="date window content",
            summary="Date-window summary.",
            source_type="normalized",
        ),
        score=2.25,
        matched_terms=("2026-04-08",),
    )

    class FakeIndex:
        def search(
            self,
            query: str,
            *,
            limit: int,
            recorded_after: object,
            recorded_before: object,
        ) -> list[SearchHit]:
            call_log.append(
                {
                    "fn": "index.search",
                    "query": query,
                    "limit": limit,
                    "recorded_after": recorded_after,
                    "recorded_before": recorded_before,
                }
            )
            return [hit]

    def fake_from_root(root: Path, *, lexical_policy: str | None = None) -> object:
        call_log.append(
            {"fn": "from_root", "root": root, "lexical_policy": lexical_policy}
        )
        return SimpleNamespace(index=FakeIndex(), lexical_policy=lexical_policy)

    def fail_known_item_lookup(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("ISO-date recall should bypass known-item lookup")

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("ISO-date recall should bypass topical fallback")

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("ISO-date recall should use date-window index search")

    monkeypatch.setattr(
        "snowiki.cli.commands.recall.RetrievalService.from_root", fake_from_root
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.known_item_lookup", fail_known_item_lookup
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.topical_recall", fail_topical_recall
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.temporal_recall", fail_temporal_recall
    )

    result = run_recall(tmp_path, "2026-04-08")

    assert result == {
        "target": "2026-04-08",
        "strategy": "date",
        "lexical_policy": "legacy-lexical",
        "lexical_policy_source": "default",
        "hits": [
            {
                "id": "session-date-window",
                "path": "normalized/session-date-window.json",
                "title": "Date window hit",
                "kind": "session",
                "score": 2.25,
                "summary": "Date-window summary.",
            }
        ],
    }
    assert call_log[0] == {
        "fn": "from_root",
        "root": tmp_path,
        "lexical_policy": "legacy-lexical",
    }
    assert call_log[1]["fn"] == "index.search"
    assert call_log[1]["query"] == "2026-04-08"
    assert call_log[1]["limit"] == 10


def test_query_hybrid_mode_still_uses_topical_recall_and_reports_disabled_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    hit = SearchHit(
        document=SearchDocument(
            id="session-2",
            path="normalized/session-2.json",
            kind="session",
            title="Hybrid query hit",
            content="hybrid query content",
            summary="Hybrid query summary.",
            source_type="normalized",
        ),
        score=4.25,
        matched_terms=("hybrid", "query"),
    )

    def fake_build_retrieval_snapshot(
        root: Path, *, lexical_policy: str | None = None
    ) -> object:
        call_log.append(
            {
                "fn": "build_retrieval_snapshot",
                "root": root,
                "lexical_policy": lexical_policy,
            }
        )
        return SimpleNamespace(
            lexical_policy=lexical_policy,
            index=runtime_index,
            records_indexed=7,
            pages_indexed=4,
        )

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "topical_recall", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    def fail_bm25(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("hybrid query should still use the runtime topical path")

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall", fake_topical_recall
    )
    monkeypatch.setattr("snowiki.search.bm25_index.BM25SearchIndex", fail_bm25)

    result = runner.invoke(
        app,
        [
            "query",
            "hybrid query",
            "--mode",
            "hybrid",
            "--top-k",
            "2",
            "--output",
            "json",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "command": "query",
        "ok": True,
        "result": {
            "query": "hybrid query",
            "mode": "hybrid",
            "lexical_policy": "legacy-lexical",
            "lexical_policy_source": "default",
            "semantic_backend": "disabled",
            "records_indexed": 7,
            "pages_indexed": 4,
            "hits": [
                {
                    "id": "session-2",
                    "path": "normalized/session-2.json",
                    "title": "Hybrid query hit",
                    "kind": "session",
                    "source_type": "normalized",
                    "score": 4.25,
                    "matched_terms": ["hybrid", "query"],
                    "summary": "Hybrid query summary.",
                }
            ],
        },
    }
    help_result = runner.invoke(app, ["query", "--help"])
    assert "hybrid" in help_result.output
    assert "lexical/no-op" in help_result.output
    assert "compatibility surface" in help_result.output
    assert call_log == [
        {
            "fn": "build_retrieval_snapshot",
            "root": tmp_path,
            "lexical_policy": "legacy-lexical",
        },
        {
            "fn": "topical_recall",
            "index": runtime_index,
            "query": "hybrid query",
            "limit": 2,
        },
    ]


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
    manifest = json.loads(
        (tmp_path / "index" / "manifest.json").read_text(encoding="utf-8")
    )

    assert result["records_indexed"] == after.records_indexed
    assert result["pages_indexed"] == after.pages_indexed
    assert after.index.size >= before_size
    assert manifest["lexical_policy"] == after.lexical_policy
    assert manifest["lexical_policy_version"] == after.lexical_policy_version


def test_retrieval_snapshot_cache_key_includes_lexical_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clear_query_search_index_cache()
    call_log: list[dict[str, object]] = []

    def fake_from_root(root: Path, *, lexical_policy: str | None = None) -> object:
        call_log.append({"root": root, "lexical_policy": lexical_policy})
        return SimpleNamespace(
            lexical_policy=lexical_policy,
            lexical=SimpleNamespace(documents=[]),
            wiki=SimpleNamespace(documents=[]),
            index=SimpleNamespace(size=0),
            records_indexed=0,
            pages_indexed=0,
        )

    monkeypatch.setattr(
        "snowiki.search.workspace.RetrievalService.from_root",
        fake_from_root,
    )

    first = build_retrieval_snapshot(tmp_path, lexical_policy="legacy-lexical")
    second = build_retrieval_snapshot(tmp_path, lexical_policy="legacy-lexical")
    third = build_retrieval_snapshot(tmp_path, lexical_policy="korean-mixed-lexical")

    assert first is second
    assert third.lexical_policy == "korean-mixed-lexical"
    assert call_log == [
        {"root": tmp_path, "lexical_policy": "legacy-lexical"},
        {"root": tmp_path, "lexical_policy": "korean-mixed-lexical"},
    ]
    clear_query_search_index_cache()


def test_build_retrieval_snapshot_requires_explicit_rebuild_on_policy_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "lexical_policy": "korean-mixed-lexical",
                "lexical_policy_version": 1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeLexicalPolicyMismatchError, match="snowiki rebuild"):
        build_retrieval_snapshot(tmp_path, lexical_policy="legacy-lexical")


def test_build_retrieval_snapshot_requires_explicit_rebuild_when_manifest_lacks_policy_metadata(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"search_documents": 0}), encoding="utf-8")

    with pytest.raises(
        RuntimeLexicalPolicyMismatchError,
        match="missing runtime lexical policy metadata",
    ):
        build_retrieval_snapshot(tmp_path)


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
    snapshot = SimpleNamespace(
        lexical_policy="legacy-lexical",
        index=runtime_index,
        records_indexed=3,
        pages_indexed=2,
    )

    def fake_build_retrieval_snapshot(
        root: Path, *, lexical_policy: str | None = None
    ) -> object:
        call_log.append(
            {
                "fn": "build_retrieval_snapshot",
                "root": root,
                "lexical_policy": lexical_policy,
            }
        )
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
        "lexical_policy": "legacy-lexical",
        "lexical_policy_source": "default",
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
        {
            "fn": "build_retrieval_snapshot",
            "root": tmp_path,
            "lexical_policy": "legacy-lexical",
        },
        {
            "fn": "topical_recall",
            "index": runtime_index,
            "query": "runtime lexical",
            "limit": 4,
        },
    ]


def test_run_query_uses_config_policy_when_cli_and_env_are_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    runtime_hit = SearchHit(
        document=SearchDocument(
            id="session-config-policy",
            path="normalized/session-config-policy.json",
            kind="session",
            title="Configured policy hit",
            content="configured policy content",
            source_type="normalized",
        ),
        score=1.75,
        matched_terms=("configured", "policy"),
    )

    def fake_build_retrieval_snapshot(
        root: Path, *, lexical_policy: str | None = None
    ) -> object:
        call_log.append(
            {
                "fn": "build_retrieval_snapshot",
                "root": root,
                "lexical_policy": lexical_policy,
            }
        )
        return SimpleNamespace(
            lexical_policy=lexical_policy,
            index=runtime_index,
            records_indexed=2,
            pages_indexed=1,
        )

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "topical_recall", "index": index, "query": query, "limit": limit}
        )
        return [runtime_hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall",
        fake_topical_recall,
    )

    result = run_query(
        tmp_path,
        "configured policy",
        mode="lexical",
        top_k=3,
        config_lexical_policy="korean-mixed-lexical",
        env={},
    )

    assert result["lexical_policy"] == "korean-mixed-lexical"
    assert result["lexical_policy_source"] == "config"
    assert call_log == [
        {
            "fn": "build_retrieval_snapshot",
            "root": tmp_path,
            "lexical_policy": "korean-mixed-lexical",
        },
        {
            "fn": "topical_recall",
            "index": runtime_index,
            "query": "configured policy",
            "limit": 3,
        },
    ]


def test_query_cli_lexical_policy_overrides_env_and_surfaces_json_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    hit = SearchHit(
        document=SearchDocument(
            id="session-cli-policy",
            path="normalized/session-cli-policy.json",
            kind="session",
            title="CLI policy hit",
            content="cli policy content",
            summary="CLI policy summary.",
            source_type="normalized",
        ),
        score=2.5,
        matched_terms=("cli", "policy"),
    )

    def fake_build_retrieval_snapshot(
        root: Path, *, lexical_policy: str | None = None
    ) -> object:
        call_log.append(
            {
                "fn": "build_retrieval_snapshot",
                "root": root,
                "lexical_policy": lexical_policy,
            }
        )
        return SimpleNamespace(
            lexical_policy=lexical_policy,
            index=runtime_index,
            records_indexed=4,
            pages_indexed=2,
        )

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "topical_recall", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall",
        fake_topical_recall,
    )

    result = runner.invoke(
        app,
        [
            "query",
            "cli policy",
            "--mode",
            "lexical",
            "--top-k",
            "2",
            "--lexical-policy",
            "legacy-lexical",
            "--output",
            "json",
        ],
        env={
            "SNOWIKI_ROOT": str(tmp_path),
            "SNOWIKI_LEXICAL_POLICY": "korean-mixed-lexical",
        },
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["lexical_policy"] == "legacy-lexical"
    assert payload["result"]["lexical_policy_source"] == "cli"
    assert call_log == [
        {
            "fn": "build_retrieval_snapshot",
            "root": tmp_path,
            "lexical_policy": "legacy-lexical",
        },
        {
            "fn": "topical_recall",
            "index": runtime_index,
            "query": "cli policy",
            "limit": 2,
        },
    ]


def test_recall_env_lexical_policy_is_used_when_cli_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    call_log: list[dict[str, object]] = []
    runtime_index = object()
    hit = SearchHit(
        document=SearchDocument(
            id="session-env-policy",
            path="normalized/session-env-policy.json",
            kind="session",
            title="Env policy hit",
            content="env policy content",
            summary="Env policy summary.",
            source_type="normalized",
        ),
        score=5.0,
        matched_terms=("env", "policy"),
    )

    def fake_from_root(root: Path, *, lexical_policy: str | None = None) -> object:
        call_log.append(
            {"fn": "from_root", "root": root, "lexical_policy": lexical_policy}
        )
        return SimpleNamespace(index=runtime_index, lexical_policy=lexical_policy)

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "known_item_lookup", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.recall.RetrievalService.from_root", fake_from_root
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.recall.known_item_lookup", fake_known_item_lookup
    )

    result = runner.invoke(
        app,
        ["recall", "env policy", "--output", "json"],
        env={
            "SNOWIKI_ROOT": str(tmp_path),
            "SNOWIKI_LEXICAL_POLICY": "korean-mixed-lexical",
        },
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"]["lexical_policy"] == "korean-mixed-lexical"
    assert payload["result"]["lexical_policy_source"] == "env"
    assert payload["result"]["strategy"] == "known_item"
    assert call_log == [
        {
            "fn": "from_root",
            "root": tmp_path,
            "lexical_policy": "korean-mixed-lexical",
        },
        {
            "fn": "known_item_lookup",
            "index": runtime_index,
            "query": "env policy",
            "limit": 10,
        },
    ]
