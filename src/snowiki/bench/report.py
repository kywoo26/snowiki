from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from .baselines import run_baseline_comparison
from .models import BenchmarkReport
from .phase1_correctness import CheckIssue, ValidationResult, validate_phase1_workspace
from .phase1_latency import run_phase1_latency_evaluation
from .presets import get_preset

_RENDER = import_module("snowiki.bench.render")
_VERDICT = import_module("snowiki.bench.verdict")


class _RenderReportText(Protocol):
    def __call__(self, report: dict[str, object]) -> str: ...


class _ReportToInt(Protocol):
    def __call__(self, report: dict[str, object]) -> int: ...


class _ReportToDict(Protocol):
    def __call__(self, report: dict[str, object]) -> dict[str, object]: ...


class _ThresholdEntries(Protocol):
    def __call__(self, report: dict[str, object]) -> list[dict[str, object]]: ...


class _ThresholdPolicy(Protocol):
    def __call__(self) -> list[dict[str, object]]: ...


class _RetrievalThresholdPolicy(Protocol):
    def __call__(self) -> dict[str, object]: ...


def _legacy_retrieval_payload(
    retrieval: BenchmarkReport | dict[str, object],
) -> dict[str, object]:
    if isinstance(retrieval, BenchmarkReport):
        return retrieval.to_legacy_dict()
    return retrieval


render_report_text = cast(_RenderReportText, _RENDER.render_report_text)
benchmark_verdict = cast(_ReportToDict, _VERDICT.benchmark_verdict)
benchmark_exit_code = cast(_ReportToInt, _VERDICT.benchmark_exit_code)
informational_warning_count = cast(_ReportToInt, _VERDICT.informational_warning_count)
performance_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.performance_threshold_failure_count
)
retrieval_threshold_failure_count = cast(
    _ReportToInt, _VERDICT.retrieval_threshold_failure_count
)
structural_failure_count = cast(_ReportToInt, _VERDICT.structural_failure_count)
_performance_threshold_entries = cast(
    _ThresholdEntries, _VERDICT._performance_threshold_entries
)
_performance_threshold_policy = cast(
    _ThresholdPolicy, _VERDICT._performance_threshold_policy
)
_retrieval_threshold_policy = cast(
    _RetrievalThresholdPolicy, _VERDICT._retrieval_threshold_policy
)


def generate_report(
    root: Path,
    *,
    preset_name: str,
) -> dict[str, object]:
    preset = get_preset(preset_name)
    structural = _structural_validation_summary(validate_phase1_workspace(root))
    performance = run_phase1_latency_evaluation(root, preset=preset)
    retrieval = _legacy_retrieval_payload(run_baseline_comparison(root, preset))
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


__all__ = [
    "benchmark_exit_code",
    "benchmark_verdict",
    "generate_report",
    "informational_warning_count",
    "performance_threshold_failure_count",
    "render_report_text",
    "retrieval_threshold_failure_count",
    "structural_failure_count",
]
