"""Benchmark threshold evaluation and unified verdict helpers."""

from __future__ import annotations

from typing import cast

from .contract import PHASE_1_THRESHOLDS, MetricThreshold

_PERFORMANCE_THRESHOLD_METRICS = {"p50_ms", "p95_ms"}
_RETRIEVAL_THRESHOLD_METRICS = {"recall_at_k", "mrr", "ndcg_at_k"}


def _threshold_to_dict(threshold: MetricThreshold) -> dict[str, object]:
    return {
        "metric": threshold.metric,
        "value": threshold.value,
        "operator": threshold.operator,
    }


def _performance_threshold_policy() -> list[dict[str, object]]:
    return [
        _threshold_to_dict(threshold)
        for threshold in PHASE_1_THRESHOLDS["overall"]
        if threshold.metric in _PERFORMANCE_THRESHOLD_METRICS
    ]


def _retrieval_threshold_policy() -> dict[str, object]:
    return {
        "overall": [
            _threshold_to_dict(threshold)
            for threshold in PHASE_1_THRESHOLDS["overall"]
            if threshold.metric in _RETRIEVAL_THRESHOLD_METRICS
        ],
        "slices": {
            kind: [
                _threshold_to_dict(threshold)
                for threshold in thresholds
                if threshold.metric in _RETRIEVAL_THRESHOLD_METRICS
            ]
            for kind, thresholds in PHASE_1_THRESHOLDS["slices"].items()
        },
    }


def _metric_delta(value: float, threshold: float) -> float:
    return abs(value - threshold)


def _performance_threshold_entry(
    flow: str,
    threshold: MetricThreshold,
    value: float,
) -> dict[str, object]:
    passes = (
        value >= threshold.value
        if threshold.operator == ">="
        else value <= threshold.value
    )
    return {
        "gate": flow,
        "metric": threshold.metric,
        "value": value,
        "delta": _metric_delta(value, threshold.value),
        "verdict": "PASS" if passes else "FAIL",
        "threshold": threshold.value,
        "warnings": [],
    }


def _performance_threshold_entries(
    report: dict[str, object],
) -> list[dict[str, object]]:
    performance = cast(dict[str, dict[str, float]], report.get("performance", {}))
    entries: list[dict[str, object]] = []
    for flow, latencies in performance.items():
        for threshold in PHASE_1_THRESHOLDS["overall"]:
            if threshold.metric not in _PERFORMANCE_THRESHOLD_METRICS:
                continue
            value = latencies.get(threshold.metric)
            if value is None:
                continue
            entries.append(_performance_threshold_entry(flow, threshold, value))
    return entries


def _retrieval_threshold_entries(
    report: dict[str, object],
) -> tuple[tuple[str, dict[str, object]], ...]:
    retrieval = cast(dict[str, object], report.get("retrieval", {}))
    baselines = cast(dict[str, dict[str, object]], retrieval.get("baselines", {}))
    if not isinstance(baselines, dict):
        return ()

    entries: list[tuple[str, dict[str, object]]] = []
    for baseline_name, baseline in baselines.items():
        quality = cast(dict[str, object], baseline.get("quality", {}))
        if not isinstance(quality, dict):
            continue
        thresholds = quality.get("thresholds", ())
        if not isinstance(thresholds, list):
            continue
        for entry in thresholds:
            if isinstance(entry, dict):
                entries.append((str(baseline_name), cast(dict[str, object], entry)))
    return tuple(entries)


def structural_failure_count(report: dict[str, object]) -> int:
    """Count structural failures in a benchmark report.

    Args:
        report: Benchmark report dictionary.

    Returns:
        The number of structural failures.
    """
    structural = cast(dict[str, object], report.get("structural", {}))
    failures = structural.get("failures", [])
    if not isinstance(failures, list):
        return 0
    return len(failures)


def informational_warning_count(report: dict[str, object]) -> int:
    """Count informational warnings in a benchmark report.

    Args:
        report: Benchmark report dictionary.

    Returns:
        The number of informational warnings.
    """
    structural = cast(dict[str, object], report.get("structural", {}))
    warnings = structural.get("warnings", [])
    if not isinstance(warnings, list):
        return 0
    return len(warnings)


def _entry_verdict(entry: object) -> str | None:
    if not isinstance(entry, dict):
        return None
    entry_dict = cast(dict[str, object], entry)
    verdict = entry_dict.get("verdict")
    return verdict if isinstance(verdict, str) else None


def retrieval_threshold_failure_count(report: dict[str, object]) -> int:
    """Count retrieval threshold failures in a benchmark report.

    Args:
        report: Benchmark report dictionary.

    Returns:
        The number of failing retrieval threshold entries.
    """
    return sum(
        1
        for _, entry in _retrieval_threshold_entries(report)
        if entry.get("verdict") == "FAIL"
    )


def performance_threshold_failure_count(report: dict[str, object]) -> int:
    """Count performance threshold failures in a benchmark report.

    Args:
        report: Benchmark report dictionary.

    Returns:
        The number of failing performance threshold entries.
    """
    entries = cast(list[object], report.get("performance_thresholds", []))
    if not isinstance(entries, list):
        return 0
    return sum(1 for entry in entries if _entry_verdict(entry) == "FAIL")


def benchmark_verdict(report: dict[str, object]) -> dict[str, object]:
    """Compute the overall benchmark verdict.

    Args:
        report: Benchmark report dictionary.

    Returns:
        A dictionary describing the benchmark verdict and stage ordering.
    """
    structural_failures = structural_failure_count(report)
    retrieval_failures = retrieval_threshold_failure_count(report)
    performance_failures = performance_threshold_failure_count(report)
    warnings = informational_warning_count(report)
    stages: list[dict[str, object]] = [
        {
            "name": "structural",
            "verdict": "FAIL" if structural_failures else "PASS",
            "blocking": True,
            "failure_count": structural_failures,
            "warning_count": warnings,
        },
        {
            "name": "retrieval_thresholds",
            "verdict": "FAIL" if retrieval_failures else "PASS",
            "blocking": True,
            "failure_count": retrieval_failures,
        },
        {
            "name": "performance_thresholds",
            "verdict": "FAIL" if performance_failures else "PASS",
            "blocking": True,
            "failure_count": performance_failures,
        },
        {
            "name": "informational",
            "verdict": "WARN" if warnings else "PASS",
            "blocking": False,
            "warning_count": warnings,
        },
    ]
    if structural_failures:
        return {
            "verdict": "FAIL",
            "exit_code": 1,
            "blocking_stage": "structural",
            "order": [stage["name"] for stage in stages],
            "stages": stages,
        }
    if retrieval_failures or performance_failures:
        return {
            "verdict": "FAIL",
            "exit_code": 1,
            "blocking_stage": "phase1_thresholds",
            "order": [stage["name"] for stage in stages],
            "stages": stages,
        }
    return {
        "verdict": "PASS",
        "exit_code": 0,
        "blocking_stage": None,
        "order": [stage["name"] for stage in stages],
        "stages": stages,
    }


def benchmark_exit_code(report: dict[str, object]) -> int:
    """Return the process exit code encoded in a benchmark report.

    Args:
        report: Benchmark report dictionary.

    Returns:
        The benchmark exit code as an integer.
    """
    verdict = cast(dict[str, object], report.get("benchmark_verdict", {}))
    exit_code = verdict.get("exit_code")
    if isinstance(exit_code, bool):
        return int(exit_code)
    if isinstance(exit_code, int):
        return exit_code
    return 0
