"""Human-readable benchmark report rendering helpers."""

from __future__ import annotations

from importlib import import_module
from typing import cast

_VERDICT = import_module("snowiki.bench.verdict")
_retrieval_threshold_entries = _VERDICT._retrieval_threshold_entries
informational_warning_count = _VERDICT.informational_warning_count
performance_threshold_failure_count = _VERDICT.performance_threshold_failure_count
retrieval_threshold_failure_count = _VERDICT.retrieval_threshold_failure_count
structural_failure_count = _VERDICT.structural_failure_count


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
    """Render a benchmark report as human-readable text.

    Args:
        report: Benchmark report dictionary.

    Returns:
        A newline-delimited text summary of the report.
    """
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
