from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any


def percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(float(item) for item in values)
    rank = max(0.0, min(1.0, value / 100.0)) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


@dataclass(frozen=True)
class LatencySummary:
    count: int
    p50_ms: float
    p95_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    durations_ms: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_latencies(durations_ms: list[float]) -> LatencySummary:
    normalized = [round(float(item), 6) for item in durations_ms]
    if not normalized:
        return LatencySummary(
            count=0,
            p50_ms=0.0,
            p95_ms=0.0,
            avg_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            durations_ms=(),
        )
    return LatencySummary(
        count=len(normalized),
        p50_ms=round(percentile(normalized, 50), 6),
        p95_ms=round(percentile(normalized, 95), 6),
        avg_ms=round(sum(normalized) / len(normalized), 6),
        min_ms=round(min(normalized), 6),
        max_ms=round(max(normalized), 6),
        durations_ms=tuple(normalized),
    )


def measure_latency(callable_: Any, inputs: list[Any]) -> LatencySummary:
    durations_ms: list[float] = []
    for item in inputs:
        started_at = time.perf_counter()
        callable_(item)
        durations_ms.append((time.perf_counter() - started_at) * 1000.0)
    return summarize_latencies(durations_ms)
