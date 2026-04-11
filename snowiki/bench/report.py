from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .baselines import run_baseline_comparison
from .contract import PHASE_1_THRESHOLDS, MetricThreshold
from .phase1_correctness import CheckIssue, ValidationResult, validate_phase1_workspace
from .phase1_latency import run_phase1_latency_evaluation
from .presets import get_preset

_PERFORMANCE_THRESHOLD_METRICS = {"p50_ms", "p95_ms"}
_RETRIEVAL_THRESHOLD_METRICS = {"recall_at_k", "mrr", "ndcg_at_k"}


def generate_report(
    root: Path,
    *,
    preset_name: str,
) -> dict[str, object]:
    preset = get_preset(preset_name)
    structural = _structural_validation_summary(validate_phase1_workspace(root))
    performance = run_phase1_latency_evaluation(root, preset=preset)
    retrieval = run_baseline_comparison(root, preset)
    report: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "report_version": "1.2",
        "preset": {
            "name": preset.name,
            "description": preset.description,
            "query_kinds": list(preset.query_kinds),
            "top_k": preset.top_k,
        },
        "structural": structural,
        "performance": performance["performance"],
        "performance_threshold_policy": _performance_threshold_policy(),
        "corpus": performance["corpus"],
        "protocol": performance["protocol"],
        "retrieval": {
            **retrieval,
            "threshold_policy": _retrieval_threshold_policy(),
        },
    }
    report["performance_thresholds"] = _performance_threshold_entries(report)
    report["benchmark_verdict"] = benchmark_verdict(report)
    return report


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


def _structural_issue_entry(stage: str, issue: CheckIssue) -> dict[str, object]:
    entry: dict[str, object] = {
        "stage": stage,
        "code": issue["code"],
        "severity": issue["severity"],
        "path": issue["path"],
        "message": issue["message"],
    }
    if "target" in issue:
        entry["target"] = issue["target"]
    return entry


def _structural_validation_summary(
    validation: ValidationResult,
) -> dict[str, object]:
    warnings = [
        _structural_issue_entry("lint", issue)
        for issue in validation["lint"]["issues"]
        if issue["severity"] != "error"
    ]
    warnings.extend(
        _structural_issue_entry("integrity", issue)
        for issue in validation["integrity"]["issues"]
        if issue["severity"] != "error"
    )
    failures = [dict(failure) for failure in validation["failures"]]
    return {
        "ok": validation["ok"],
        "error_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }


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


def _render_thresholds(thresholds: object) -> str:
    if not isinstance(thresholds, list):
        return ""
    rendered: list[str] = []
    for entry in thresholds:
        if not isinstance(entry, dict):
            continue
        threshold = cast(dict[str, object], entry)
        metric = str(threshold.get("metric", "unknown"))
        operator = str(threshold.get("operator", ">="))
        value = threshold.get("value", "n/a")
        rendered.append(f"{metric} {operator} {value}")
    return ", ".join(rendered)


def structural_failure_count(report: dict[str, object]) -> int:
    structural = cast(dict[str, object], report.get("structural", {}))
    failures = structural.get("failures", [])
    if not isinstance(failures, list):
        return 0
    return len(failures)


def informational_warning_count(report: dict[str, object]) -> int:
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
    return sum(
        1
        for _, entry in _retrieval_threshold_entries(report)
        if entry.get("verdict") == "FAIL"
    )


def performance_threshold_failure_count(report: dict[str, object]) -> int:
    entries = cast(list[object], report.get("performance_thresholds", []))
    if not isinstance(entries, list):
        return 0
    return sum(1 for entry in entries if _entry_verdict(entry) == "FAIL")


def benchmark_verdict(report: dict[str, object]) -> dict[str, object]:
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
    verdict = cast(dict[str, object], report.get("benchmark_verdict", {}))
    exit_code = verdict.get("exit_code")
    if isinstance(exit_code, bool):
        return int(exit_code)
    if isinstance(exit_code, int):
        return exit_code
    return 0


def _format_threshold_entry(baseline: str, entry: dict[str, object]) -> str:
    gate = str(entry.get("gate", "unknown"))
    metric = str(entry.get("metric", "unknown"))
    value = entry.get("value", "n/a")
    delta = entry.get("delta")
    threshold = entry.get("threshold", "n/a")
    verdict = str(entry.get("verdict", "UNKNOWN"))
    parts = [
        f"- {baseline} {gate} {metric}: {verdict}",
        f"value={value}",
        f"delta={delta if delta is not None else 'n/a'}",
        f"threshold={threshold}",
    ]
    return ", ".join(parts)


def _format_structural_issue(entry: dict[str, object]) -> str:
    return (
        f"- {entry.get('stage', 'structural')} {entry.get('code', 'unknown')}: "
        f"{entry.get('path', 'unknown')} - {entry.get('message', 'n/a')}"
    )


def _format_performance_threshold_entry(entry: dict[str, object]) -> str:
    gate = str(entry.get("gate", "unknown"))
    metric = str(entry.get("metric", "unknown"))
    value = entry.get("value", "n/a")
    delta = entry.get("delta")
    threshold = entry.get("threshold", "n/a")
    verdict = str(entry.get("verdict", "UNKNOWN"))
    return (
        f"- {gate} {metric}: {verdict}, value={value}, "
        f"delta={delta if delta is not None else 'n/a'}, threshold={threshold}"
    )


def render_report_text(report: dict[str, object]) -> str:
    preset = cast(dict[str, object], report["preset"])
    corpus = cast(dict[str, object], report["corpus"])
    protocol = cast(dict[str, object], report["protocol"])
    structural = cast(dict[str, object], report.get("structural", {}))
    retrieval = cast(dict[str, object], report["retrieval"])
    performance = cast(dict[str, dict[str, float]], report["performance"])
    performance_threshold_policy = cast(
        list[dict[str, object]], report.get("performance_threshold_policy", [])
    )
    performance_thresholds = cast(
        list[dict[str, object]], report.get("performance_thresholds", [])
    )
    unified_verdict = cast(dict[str, object], report.get("benchmark_verdict", {}))
    structural_failures = structural_failure_count(report)
    structural_warnings = informational_warning_count(report)
    lines = [
        f"Benchmark preset: {preset['name']}",
        f"Description: {preset['description']}",
        f"Queries evaluated: {corpus['queries_evaluated']}",
        f"Canonical fixtures: {corpus['fixtures_indexed']}",
        (
            "Protocol: "
            f"isolated_root={protocol['isolated_root']}, "
            f"warmups={protocol['warmups']}, "
            f"repetitions={protocol['repetitions']}, "
            f"query_mode={protocol['query_mode']}, "
            f"top_k={protocol['top_k']}"
        ),
        (
            "Structural verdict: "
            f"{'FAIL' if structural_failures else 'PASS'} "
            f"({structural_failures} failures, {structural_warnings} warnings)"
        ),
    ]
    failures = structural.get("failures", [])
    if isinstance(failures, list) and failures:
        lines.append("Structural failures:")
        for entry in failures:
            if isinstance(entry, dict):
                lines.append(_format_structural_issue(cast(dict[str, object], entry)))
    warnings = structural.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Informational warnings:")
        for entry in warnings:
            if isinstance(entry, dict):
                lines.append(_format_structural_issue(cast(dict[str, object], entry)))
    lines.append("Performance:")
    for name, latency in performance.items():
        lines.append(f"- {name}: P50={latency['p50_ms']}ms, P95={latency['p95_ms']}ms")
    if performance_threshold_policy:
        lines.append("Performance threshold policy:")
        lines.append(f"- overall: {_render_thresholds(performance_threshold_policy)}")
    performance_failures = [
        entry for entry in performance_thresholds if entry.get("verdict") == "FAIL"
    ]
    if performance_failures:
        lines.append("Performance threshold failures:")
        for entry in performance_failures:
            lines.append(_format_performance_threshold_entry(entry))
    if performance_thresholds:
        lines.append("Performance thresholds:")
        for entry in performance_thresholds:
            if performance_failures and entry.get("verdict") == "FAIL":
                continue
            lines.append(_format_performance_threshold_entry(entry))
        failure_count = performance_threshold_failure_count(report)
        lines.append(
            f"Performance threshold verdict: {'FAIL' if failure_count else 'PASS'} ({failure_count} failures)"
        )
    threshold_policy = cast(dict[str, object], retrieval.get("threshold_policy", {}))
    overall_policy = threshold_policy.get("overall", [])
    slice_policy = threshold_policy.get("slices", {})
    if overall_policy or slice_policy:
        lines.append("Retrieval threshold policy:")
        if isinstance(overall_policy, list) and overall_policy:
            rendered_overall = _render_thresholds(overall_policy)
            lines.append(f"- overall: {rendered_overall}")
        if isinstance(slice_policy, dict):
            for kind, thresholds in slice_policy.items():
                rendered_slice = _render_thresholds(thresholds)
                if not rendered_slice:
                    continue
                lines.append(f"- slice:{kind}: {rendered_slice}")
    threshold_entries = _retrieval_threshold_entries(report)
    if threshold_entries:
        retrieval_failures = [
            (baseline_name, entry)
            for baseline_name, entry in threshold_entries
            if entry.get("verdict") == "FAIL"
        ]
        if retrieval_failures:
            lines.append("Retrieval threshold failures:")
            for baseline_name, entry in retrieval_failures:
                lines.append(_format_threshold_entry(baseline_name, entry))
        lines.append("Retrieval thresholds:")
        for baseline_name, entry in threshold_entries:
            if retrieval_failures and entry.get("verdict") == "FAIL":
                continue
            lines.append(_format_threshold_entry(baseline_name, entry))
        failure_count = retrieval_threshold_failure_count(report)
        lines.append(
            f"Retrieval threshold verdict: {'FAIL' if failure_count else 'PASS'} ({failure_count} failures)"
        )
    lines.append(
        "Unified benchmark verdict: "
        f"{unified_verdict.get('verdict', 'UNKNOWN')} "
        f"(blocking_stage={unified_verdict.get('blocking_stage')}, "
        f"exit_code={unified_verdict.get('exit_code', 'n/a')})"
    )
    return "\n".join(lines)
