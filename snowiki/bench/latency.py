from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass


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
    p50_ms: float
    p95_ms: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def summarize_latencies(durations_ms: list[float]) -> LatencySummary:
    normalized = [round(float(item), 6) for item in durations_ms]
    if not normalized:
        return LatencySummary(
            p50_ms=0.0,
            p95_ms=0.0,
        )
    return LatencySummary(
        p50_ms=round(percentile(normalized, 50), 6),
        p95_ms=round(percentile(normalized, 95), 6),
    )


def measure_operation(
    operation: Callable[[], object],
    *,
    warmups: int = 0,
    repetitions: int = 1,
    clock: Callable[[], float] = time.perf_counter,
) -> LatencySummary:
    for _ in range(max(0, warmups)):
        _ = operation()

    durations_ms: list[float] = []
    for _ in range(max(0, repetitions)):
        started_at = clock()
        _ = operation()
        durations_ms.append((clock() - started_at) * 1000.0)
    return summarize_latencies(durations_ms)


def measure_latency[T](
    callable_: Callable[[T], object],
    inputs: list[T],
    *,
    warmups: int = 0,
    repetitions: int = 1,
    clock: Callable[[], float] = time.perf_counter,
) -> LatencySummary:
    durations_ms: list[float] = []
    for item in inputs:
        for _ in range(max(0, warmups)):
            _ = callable_(item)
        for _ in range(max(0, repetitions)):
            started_at = clock()
            _ = callable_(item)
            durations_ms.append((clock() - started_at) * 1000.0)
    return summarize_latencies(durations_ms)
