from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_LATENCY = import_module("snowiki.bench.latency")
measure_latency = _LATENCY.measure_latency
percentile = _LATENCY.percentile
summarize_latencies = _LATENCY.summarize_latencies


def test_percentile_uses_linear_interpolation() -> None:
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == 25.0
    assert percentile(values, 95) == 38.5


def test_summarize_latencies_returns_p50_and_p95() -> None:
    summary = summarize_latencies([5.0, 10.0, 15.0, 20.0])

    assert summary.count == 4
    assert summary.p50_ms == 12.5
    assert summary.p95_ms == 19.25
    assert summary.avg_ms == 12.5
    assert summary.min_ms == 5.0
    assert summary.max_ms == 20.0


def test_measure_latency_executes_callable_for_each_input() -> None:
    seen: list[int] = []

    def record(value: int) -> None:
        seen.append(value)

    summary = measure_latency(record, [1, 2, 3])

    assert seen == [1, 2, 3]
    assert summary.count == 3
    assert summary.p50_ms >= 0.0
    assert summary.p95_ms >= summary.p50_ms
