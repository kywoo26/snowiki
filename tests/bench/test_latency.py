from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from snowiki.bench.latency import (  # noqa: E402
    measure_latency,
    measure_operation,
    percentile,
    summarize_latencies,
)


def test_percentile_uses_linear_interpolation() -> None:
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 25.0
    assert percentile(values, 95) == 38.5


def test_summarize_latencies_returns_p50_and_p95() -> None:
    summary = summarize_latencies([5.0, 10.0, 15.0, 20.0])

    assert summary.p50_ms == 12.5
    assert summary.p95_ms == 19.25
    assert summary.to_dict() == {"p50_ms": 12.5, "p95_ms": 19.25}


def test_measure_operation_excludes_warmups_from_summary() -> None:
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


def test_measure_latency_executes_callable_for_each_input() -> None:
    seen: list[int] = []

    def record(value: int) -> None:
        seen.append(value)

    summary = measure_latency(record, [1, 2, 3])

    assert seen == [1, 2, 3]
    assert summary.p50_ms >= 0.0
    assert summary.p95_ms >= summary.p50_ms


def test_measure_latency_excludes_warmups_per_input() -> None:
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
