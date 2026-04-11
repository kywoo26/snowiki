from __future__ import annotations

import time
from pathlib import Path
from typing import cast

import pytest

from snowiki.bench import phase1_latency
from snowiki.bench.presets import get_preset

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
        "_load_queries_for_preset",
        lambda _preset: ("first query", "second query"),
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
    }
    assert corpus["fixtures_indexed"] == 2
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
