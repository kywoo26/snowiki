from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from snowiki.bench.contract.presets import get_preset
from snowiki.bench.validation import latency as phase1_latency
from snowiki.search.indexer import SearchDocument, SearchHit

run_phase1_latency_evaluation = phase1_latency.run_phase1_latency_evaluation


def test_phase1_latency_evaluation_covers_all_flows_with_isolated_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claude_fixture = tmp_path / "basic.jsonl"
    _ = claude_fixture.write_text("{}\n", encoding="utf-8")
    omo_fixture = tmp_path / "basic.db"
    _ = omo_fixture.write_bytes(b"fixture")

    monkeypatch.setattr(phase1_latency, "PHASE_1_WARMUPS", 1)
    monkeypatch.setattr(phase1_latency, "PHASE_1_REPETITIONS", 2)
    monkeypatch.setattr(
        phase1_latency,
        "_canonical_fixtures",
        lambda: (
            {"source": "claude", "path": claude_fixture},
            {"source": "opencode", "path": omo_fixture},
        ),
    )
    monkeypatch.setattr(
        phase1_latency,
        "_load_query_specs_for_preset",
        lambda _preset, manifest=None: (
            {"text": "first query", "kind": "known-item"},
            {"text": "second query", "kind": "known-item"},
        ),
    )

    ingest_roots: list[Path] = []
    rebuild_roots: list[Path] = []
    query_roots: list[Path] = []

    def fake_ingest(path: Path, *, source: str, root: Path) -> dict[str, object]:
        ingest_roots.append(root)
        return {"path": path.as_posix(), "source": source, "root": root.as_posix()}

    def fake_rebuild(root: Path) -> dict[str, object]:
        rebuild_roots.append(root)
        return {"root": root.as_posix()}

    def fake_query(
        root: Path, query: str, *, mode: str, top_k: int
    ) -> dict[str, object]:
        query_roots.append(root)
        return {
            "root": root.as_posix(),
            "query": query,
            "mode": mode,
            "top_k": top_k,
        }

    monkeypatch.setattr(phase1_latency, "run_ingest", fake_ingest)
    monkeypatch.setattr(phase1_latency, "run_rebuild", fake_rebuild)
    monkeypatch.setattr(phase1_latency, "run_query", fake_query)

    ticks = iter([0.0, 1.0, 10.0, 13.0, 20.0, 21.0, 30.0, 34.0, 40.0, 41.0, 50.0, 55.0])
    monkeypatch.setattr(time, "perf_counter", lambda: next(ticks))

    report = run_phase1_latency_evaluation(
        tmp_path / "requested-root", preset=get_preset("core")
    )
    protocol = cast(dict[str, object], report["protocol"])
    corpus = cast(dict[str, object], report["corpus"])
    performance = cast(dict[str, dict[str, float]], report["performance"])

    assert protocol == {
        "isolated_root": True,
        "warmups": 1,
        "repetitions": 2,
        "query_mode": "lexical",
        "top_k": 5,
        "top_ks": [1, 3, 5, 10, 20],
        "sampling_policy": {
            "mode": "exhaustive",
            "population_query_count": 2,
            "sampled_query_count": 2,
            "sampled": False,
        },
    }
    assert corpus["dataset"] == "regression"
    assert corpus["tier"] == "regression_harness"
    assert corpus["fixtures_indexed"] == 2
    assert corpus["queries_available"] == 2
    assert corpus["queries_evaluated"] == 2
    assert set(performance) == {"ingest", "rebuild", "query"}
    assert performance["ingest"] == {
        "p50_ms": 2000.0,
        "p95_ms": 2900.0,
        "mean_ms": 2000.0,
        "min_ms": 1000.0,
        "max_ms": 3000.0,
    }
    assert performance["rebuild"] == {
        "p50_ms": 2500.0,
        "p95_ms": 3850.0,
        "mean_ms": 2500.0,
        "min_ms": 1000.0,
        "max_ms": 4000.0,
    }
    assert performance["query"] == {
        "p50_ms": 3000.0,
        "p95_ms": 4800.0,
        "mean_ms": 3000.0,
        "min_ms": 1000.0,
        "max_ms": 5000.0,
    }

    unique_ingest_roots = {path.as_posix() for path in ingest_roots}
    unique_rebuild_roots = {path.as_posix() for path in rebuild_roots}
    unique_query_roots = {path.as_posix() for path in query_roots}

    assert len(unique_ingest_roots) == 9
    assert len(unique_rebuild_roots) == 6
    assert len(unique_query_roots) == 3
    assert all("requested-root" not in root for root in unique_ingest_roots)


def test_phase1_latency_evaluation_keeps_runtime_query_mode_lexical_with_expanded_benchmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claude_fixture = tmp_path / "basic.jsonl"
    _ = claude_fixture.write_text("{}\n", encoding="utf-8")

    def fake_canonical_fixtures() -> tuple[dict[str, object], ...]:
        return ({"source": "claude", "path": claude_fixture},)

    def fake_load_query_specs_for_preset(
        _preset: object, manifest=None
    ) -> tuple[dict[str, object], dict[str, object]]:
        return (
            {"text": "first query", "kind": "known-item"},
            {"text": "second query", "kind": "topical"},
        )

    def fake_ingest(path: Path, *, source: str, root: Path) -> dict[str, object]:
        return {"path": path.as_posix(), "source": source, "root": root.as_posix()}

    def fake_rebuild(root: Path) -> dict[str, object]:
        return {"root": root.as_posix()}

    monkeypatch.setattr(phase1_latency, "PHASE_1_WARMUPS", 0)
    monkeypatch.setattr(phase1_latency, "PHASE_1_REPETITIONS", 1)
    monkeypatch.setattr(phase1_latency, "_canonical_fixtures", fake_canonical_fixtures)
    monkeypatch.setattr(
        phase1_latency,
        "_load_query_specs_for_preset",
        fake_load_query_specs_for_preset,
    )

    query_calls: list[dict[str, object]] = []

    monkeypatch.setattr(phase1_latency, "run_ingest", fake_ingest)
    monkeypatch.setattr(phase1_latency, "run_rebuild", fake_rebuild)

    def fake_query(
        root: Path, query: str, *, mode: str, top_k: int
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "root": root.as_posix(),
            "query": query,
            "mode": mode,
            "top_k": top_k,
        }
        query_calls.append(payload)
        return payload

    monkeypatch.setattr(phase1_latency, "run_query", fake_query)

    ticks = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr(time, "perf_counter", lambda: next(ticks))

    report = run_phase1_latency_evaluation(
        tmp_path / "requested-root", preset=get_preset("retrieval")
    )

    assert report["protocol"] == {
        "isolated_root": True,
        "warmups": 0,
        "repetitions": 1,
        "query_mode": "lexical",
        "top_k": 5,
        "top_ks": [1, 3, 5, 10, 20],
        "sampling_policy": {
            "mode": "exhaustive",
            "population_query_count": 2,
            "sampled_query_count": 2,
            "sampled": False,
        },
    }
    assert list(get_preset("retrieval").baselines) == [
        "lexical",
        "bm25s",
        "bm25s_kiwi_nouns",
        "bm25s_kiwi_full",
        "bm25s_mecab_full",
        "bm25s_hf_wordpiece",
    ]
    assert [call["mode"] for call in query_calls] == ["lexical", "lexical"]
    assert [call["query"] for call in query_calls] == ["first query", "second query"]


def test_phase1_latency_keeps_benchmark_lexical_mode_and_shipped_query_hybrid_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claude_fixture = tmp_path / "basic.jsonl"
    _ = claude_fixture.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(phase1_latency, "PHASE_1_WARMUPS", 0)
    monkeypatch.setattr(phase1_latency, "PHASE_1_REPETITIONS", 1)
    monkeypatch.setattr(
        phase1_latency,
        "_canonical_fixtures",
        lambda: ({"source": "claude", "path": claude_fixture},),
    )
    monkeypatch.setattr(
        phase1_latency,
        "_load_query_specs_for_preset",
        lambda _preset, manifest=None: ({"text": "comparison query", "kind": "known-item"},),
    )

    benchmark_calls: list[dict[str, object]] = []

    def fake_benchmark_query(
        root: Path, query: str, *, mode: str, top_k: int
    ) -> dict[str, object]:
        benchmark_calls.append(
            {"root": root, "query": query, "mode": mode, "top_k": top_k}
        )
        return {"root": root.as_posix(), "query": query, "mode": mode, "top_k": top_k}

    monkeypatch.setattr(phase1_latency, "run_query", fake_benchmark_query)

    ticks = iter([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    monkeypatch.setattr(time, "perf_counter", lambda: next(ticks))

    report = run_phase1_latency_evaluation(
        tmp_path / "requested-root", preset=get_preset("retrieval")
    )
    protocol = cast(dict[str, object], report["protocol"])

    assert protocol == {
        "isolated_root": True,
        "warmups": 0,
        "repetitions": 1,
        "query_mode": "lexical",
        "top_k": 5,
        "top_ks": [1, 3, 5, 10, 20],
        "sampling_policy": {
            "mode": "exhaustive",
            "population_query_count": 1,
            "sampled_query_count": 1,
            "sampled": False,
        },
    }
    assert "semantic_backend" not in protocol
    assert len(benchmark_calls) == 1
    assert benchmark_calls[0]["query"] == "comparison query"
    assert benchmark_calls[0]["mode"] == "lexical"
    assert benchmark_calls[0]["top_k"] == 5

    from snowiki.cli.commands.query import run_query as shipped_run_query

    query_index = object()
    hit = SearchHit(
        document=SearchDocument(
            id="session-lexical",
            path="normalized/session-lexical.json",
            kind="session",
            title="Shipped query hit",
            content="shipped query content",
            summary="Shipped query summary.",
            source_type="normalized",
        ),
        score=5.5,
        matched_terms=("comparison", "query"),
    )

    def fake_build_retrieval_snapshot(root: Path) -> object:
        return SimpleNamespace(index=query_index, records_indexed=11, pages_indexed=6)

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        assert index is query_index
        assert query == "comparison query"
        assert limit == 5
        return [hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall", fake_topical_recall
    )

    lexical_result = shipped_run_query(
        tmp_path, "comparison query", mode="lexical", top_k=5
    )
    hybrid_result = shipped_run_query(
        tmp_path, "comparison query", mode="hybrid", top_k=5
    )

    assert lexical_result["semantic_backend"] is None
    assert hybrid_result["semantic_backend"] == "disabled"
    assert lexical_result["hits"] == hybrid_result["hits"]

    assert protocol["query_mode"] == "lexical"
    assert hybrid_result["mode"] == "hybrid"
    assert hybrid_result["semantic_backend"] == "disabled"
