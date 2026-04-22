from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_latency_symbols() -> tuple[Any, Any, Any, Any]:
    from snowiki.bench.runtime.latency import (
        measure_latency,
        measure_operation,
        percentile,
        summarize_latencies,
    )

    return measure_latency, measure_operation, percentile, summarize_latencies


def test_percentile_uses_linear_interpolation(repo_root: Path) -> None:
    _, _, percentile, _ = _load_latency_symbols()
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 25.0
    assert percentile(values, 95) == 38.5


def test_summarize_latencies_returns_p50_and_p95(repo_root: Path) -> None:
    _, _, _, summarize_latencies = _load_latency_symbols()
    summary = summarize_latencies([5.0, 10.0, 15.0, 20.0])

    assert summary.p50_ms == 12.5
    assert summary.p95_ms == 19.25
    assert summary.mean_ms == 12.5
    assert summary.min_ms == 5.0
    assert summary.max_ms == 20.0
    assert summary.to_dict() == {
        "p50_ms": 12.5,
        "p95_ms": 19.25,
        "mean_ms": 12.5,
        "min_ms": 5.0,
        "max_ms": 20.0,
    }


def test_measure_operation_excludes_warmups_from_summary(repo_root: Path) -> None:
    _, measure_operation, _, _ = _load_latency_symbols()
    calls: list[str] = []
    ticks = iter([0.0, 1.0, 10.0, 13.0])

    def operation() -> None:
        calls.append("run")

    summary = measure_operation(
        operation,
        warmups=1,
        repetitions=2,
        clock=lambda: next(ticks),
    )

    assert calls == ["run", "run", "run"]
    assert summary.p50_ms == 2000.0
    assert summary.p95_ms == 2900.0
    assert summary.mean_ms == 2000.0
    assert summary.min_ms == 1000.0
    assert summary.max_ms == 3000.0


def test_measure_latency_executes_callable_for_each_input(repo_root: Path) -> None:
    measure_latency, _, _, _ = _load_latency_symbols()
    seen: list[int] = []

    def record(value: int) -> None:
        seen.append(value)

    summary = measure_latency(record, [1, 2, 3])

    assert seen == [1, 2, 3]
    assert summary.p50_ms >= 0.0
    assert summary.p95_ms >= summary.p50_ms
    assert summary.mean_ms >= summary.min_ms
    assert summary.max_ms >= summary.p95_ms


def test_measure_latency_excludes_warmups_per_input(repo_root: Path) -> None:
    measure_latency, _, _, _ = _load_latency_symbols()
    seen: list[int] = []
    ticks = iter([0.0, 1.0, 10.0, 12.0, 20.0, 23.0, 30.0, 34.0])

    def record(value: int) -> None:
        seen.append(value)

    summary = measure_latency(
        record,
        [1, 2],
        warmups=1,
        repetitions=2,
        clock=lambda: next(ticks),
    )

    assert seen == [1, 1, 1, 2, 2, 2]
    assert summary.p50_ms == 2500.0
    assert summary.p95_ms == 3850.0
    assert summary.mean_ms == 2500.0
    assert summary.min_ms == 1000.0
    assert summary.max_ms == 4000.0
