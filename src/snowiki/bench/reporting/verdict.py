"""Benchmark threshold evaluation and unified verdict helpers."""

from __future__ import annotations

from typing import cast

from ..contract import (
    BENCHMARK_THRESHOLDS,
    STEP_03_CANDIDATE_POLICY,
    CandidatePolicyThresholds,
    MetricThreshold,
)
from ..evaluation.candidates import CANDIDATE_MATRIX
from ..runtime.context import get_execution_layer_policy
from .models import (
    BaselineResult,
    CandidateDecision,
    CandidateMatrixEntry,
    CandidateMatrixReport,
)

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
        for threshold in BENCHMARK_THRESHOLDS["overall"]
        if threshold.metric in _PERFORMANCE_THRESHOLD_METRICS
    ]


def _retrieval_threshold_policy() -> dict[str, object]:
    return {
        "overall": [
            _threshold_to_dict(threshold)
            for threshold in BENCHMARK_THRESHOLDS["overall"]
            if threshold.metric in _RETRIEVAL_THRESHOLD_METRICS
        ],
        "slices": {
            kind: [
                _threshold_to_dict(threshold)
                for threshold in thresholds
                if threshold.metric in _RETRIEVAL_THRESHOLD_METRICS
            ]
            for kind, thresholds in BENCHMARK_THRESHOLDS["slices"].items()
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
        for threshold in BENCHMARK_THRESHOLDS["overall"]:
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
        tokenizer_name = baseline.get("tokenizer_name")
        for entry in thresholds:
            if isinstance(entry, dict):
                entry_copy = dict(cast(dict[str, object], entry))
                if tokenizer_name:
                    entry_copy["tokenizer_name"] = tokenizer_name
                entries.append((str(baseline_name), entry_copy))
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


def _report_tier(report: dict[str, object]) -> str:
    metadata = cast(dict[str, object], report.get("metadata", {}))
    dataset_tier = metadata.get("dataset_tier")
    if isinstance(dataset_tier, str) and dataset_tier:
        return dataset_tier

    dataset = cast(dict[str, object], report.get("dataset", {}))
    dataset_tier = dataset.get("tier")
    if isinstance(dataset_tier, str) and dataset_tier:
        return dataset_tier
    return "regression_harness"


def _evaluate_policy_stages(
    *,
    structural_failures: int,
    retrieval_failures: int,
    performance_failures: int,
    warnings: int,
    tier: str,
    layer: str | None = None,
) -> list[dict[str, object]]:
    retrieval_blocking = tier == "regression_harness"
    if layer is not None:
        try:
            retrieval_blocking = get_execution_layer_policy(layer).blocking
        except ValueError:
            retrieval_blocking = tier == "regression_harness"
    return [
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
            "blocking": retrieval_blocking,
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


def _report_layer(report: dict[str, object]) -> str | None:
    metadata = cast(dict[str, object], report.get("metadata", {}))
    layer = metadata.get("execution_layer")
    if isinstance(layer, str) and layer:
        return layer
    return None


def benchmark_verdict(
    report: dict[str, object], *, tier: str | None = None
) -> dict[str, object]:
    dataset_tier = tier or _report_tier(report)
    layer = _report_layer(report)
    structural_failures = structural_failure_count(report)
    retrieval_failures = retrieval_threshold_failure_count(report)
    performance_failures = performance_threshold_failure_count(report)
    warnings = informational_warning_count(report)
    stages = _evaluate_policy_stages(
        structural_failures=structural_failures,
        retrieval_failures=retrieval_failures,
        performance_failures=performance_failures,
        warnings=warnings,
        tier=dataset_tier,
        layer=layer,
    )
    threshold_failures = [
        stage for stage in stages if stage["name"] != "structural" and stage["blocking"]
    ]
    if structural_failures:
        return {
            "verdict": "FAIL",
            "exit_code": 1,
            "blocking_stage": "structural",
            "order": [stage["name"] for stage in stages],
            "stages": stages,
        }
    if any(stage["verdict"] == "FAIL" for stage in threshold_failures):
        return {
            "verdict": "FAIL",
            "exit_code": 1,
            "blocking_stage": "performance_thresholds",
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


def evaluate_candidate_policy(
    candidate_matrix: CandidateMatrixReport,
) -> tuple[CandidateDecision, ...]:
    thresholds = STEP_03_CANDIDATE_POLICY["thresholds"]
    control_entry = _decision_entry(
        candidate_matrix,
        STEP_03_CANDIDATE_POLICY["control_candidate_name"],
        STEP_03_CANDIDATE_POLICY["control_decision_baseline"],
    )
    decisions: list[CandidateDecision] = []

    for candidate in CANDIDATE_MATRIX:
        entry = _decision_entry(
            candidate_matrix, candidate.candidate_name, candidate.evidence_baseline
        )
        if candidate.control:
            decisions.append(_control_decision(entry))
            continue
        decisions.append(
            _candidate_decision(
                entry,
                control_entry,
                thresholds,
                candidate_name=candidate.candidate_name,
                evidence_baseline=candidate.evidence_baseline,
            )
        )

    return tuple(decisions)


def _decision_entry(
    candidate_matrix: CandidateMatrixReport,
    candidate_name: str,
    evidence_baseline: str | None,
) -> CandidateMatrixEntry | None:
    for entry in candidate_matrix.candidates:
        if entry.candidate_name != candidate_name:
            continue
        if entry.evidence_baseline == evidence_baseline:
            return entry
    return None


def _control_decision(entry: CandidateMatrixEntry | None) -> CandidateDecision:
    if entry is None or entry.baseline is None:
        return CandidateDecision(
            candidate_name=STEP_03_CANDIDATE_POLICY["control_candidate_name"],
            evidence_baseline=STEP_03_CANDIDATE_POLICY["control_decision_baseline"],
            disposition="reject",
            overall_quality_gate_passed=False,
            operational_evidence_present=False,
            mixed_deltas=dict.fromkeys(
                STEP_03_CANDIDATE_POLICY["mixed_delta_metrics"], 0.0
            ),
            ko_recall_delta=0.0,
            en_recall_delta=0.0,
            latency_p95_ratio=None,
            reasons=["missing_control_evidence"],
        )

    overall_pass = _passes_overall_quality_gates(entry.baseline)
    operational_present = _has_usable_operational_evidence(entry)
    return CandidateDecision(
        candidate_name=entry.candidate_name,
        evidence_baseline=entry.evidence_baseline,
        disposition=(
            "promote"
            if overall_pass and operational_present
            else "benchmark_only"
            if overall_pass
            else "reject"
        ),
        overall_quality_gate_passed=overall_pass,
        operational_evidence_present=operational_present,
        mixed_deltas=dict.fromkeys(
            STEP_03_CANDIDATE_POLICY["mixed_delta_metrics"], 0.0
        ),
        ko_recall_delta=0.0,
        en_recall_delta=0.0,
        latency_p95_ratio=1.0,
        reasons=(
            []
            if overall_pass and operational_present
            else ["missing_operational_evidence"]
            if overall_pass
            else ["overall_quality_gate_failed"]
        ),
    )


def _candidate_decision(
    entry: CandidateMatrixEntry | None,
    control_entry: CandidateMatrixEntry | None,
    thresholds: object,
    *,
    candidate_name: str,
    evidence_baseline: str | None,
) -> CandidateDecision:
    mixed_metrics = tuple(STEP_03_CANDIDATE_POLICY["mixed_delta_metrics"])
    if (
        entry is None
        or entry.baseline is None
        or control_entry is None
        or control_entry.baseline is None
    ):
        return CandidateDecision(
            candidate_name=entry.candidate_name if entry else candidate_name,
            evidence_baseline=entry.evidence_baseline if entry else evidence_baseline,
            disposition="reject",
            overall_quality_gate_passed=False,
            operational_evidence_present=bool(entry and entry.operational_evidence),
            reasons=["missing_benchmark_evidence"],
        )

    mixed_deltas = {
        metric: _group_metric_delta(
            entry.baseline, control_entry.baseline, "mixed", metric
        )
        for metric in mixed_metrics
    }
    ko_recall_delta = _group_metric_delta(
        entry.baseline, control_entry.baseline, "ko", "recall_at_k"
    )
    en_recall_delta = _group_metric_delta(
        entry.baseline, control_entry.baseline, "en", "recall_at_k"
    )
    latency_ratio = _latency_ratio(entry.baseline, control_entry.baseline)
    overall_pass = _passes_overall_quality_gates(entry.baseline)
    operational_present = _has_usable_operational_evidence(entry)
    threshold_values = cast(CandidatePolicyThresholds, thresholds)
    mixed_min = threshold_values.mixed_delta_min
    recall_floor = threshold_values.slice_recall_non_regression_floor
    latency_max = threshold_values.latency_p95_ratio_max

    if not overall_pass:
        return CandidateDecision(
            candidate_name=entry.candidate_name,
            evidence_baseline=entry.evidence_baseline,
            disposition="reject",
            overall_quality_gate_passed=False,
            operational_evidence_present=operational_present,
            mixed_deltas=mixed_deltas,
            ko_recall_delta=ko_recall_delta,
            en_recall_delta=en_recall_delta,
            latency_p95_ratio=latency_ratio,
            reasons=["overall_quality_gate_failed"],
        )

    if not any(delta > 0.0 for delta in mixed_deltas.values()):
        return CandidateDecision(
            candidate_name=entry.candidate_name,
            evidence_baseline=entry.evidence_baseline,
            disposition="reject",
            overall_quality_gate_passed=True,
            operational_evidence_present=operational_present,
            mixed_deltas=mixed_deltas,
            ko_recall_delta=ko_recall_delta,
            en_recall_delta=en_recall_delta,
            latency_p95_ratio=latency_ratio,
            reasons=["no_material_mixed_improvement"],
        )

    reasons: list[str] = []
    if any(delta < mixed_min for delta in mixed_deltas.values()):
        reasons.append("mixed_delta_below_promotion_threshold")
    if ko_recall_delta < recall_floor or en_recall_delta < recall_floor:
        reasons.append("slice_recall_non_regression_failed")
    if latency_ratio > latency_max:
        reasons.append("latency_ratio_guard_failed")
    if not operational_present:
        reasons.append("missing_operational_evidence")

    return CandidateDecision(
        candidate_name=entry.candidate_name,
        evidence_baseline=entry.evidence_baseline,
        disposition="benchmark_only" if reasons else "promote",
        overall_quality_gate_passed=True,
        operational_evidence_present=operational_present,
        mixed_deltas=mixed_deltas,
        ko_recall_delta=ko_recall_delta,
        en_recall_delta=en_recall_delta,
        latency_p95_ratio=latency_ratio,
        reasons=reasons,
    )


def _passes_overall_quality_gates(baseline: BaselineResult) -> bool:
    quality = baseline.quality
    if quality is None:
        return False
    thresholds = quality.thresholds
    overall_entries = [entry for entry in thresholds if entry.gate == "overall"]
    if not overall_entries:
        return False
    return all(entry.verdict != "FAIL" for entry in overall_entries)


def _group_metric_delta(
    candidate: BaselineResult,
    control: BaselineResult,
    group: str,
    metric: str,
) -> float:
    candidate_value = _group_metric(candidate, group, metric)
    control_value = _group_metric(control, group, metric)
    return round(candidate_value - control_value, 6)


def _group_metric(baseline: BaselineResult, group: str, metric: str) -> float:
    quality = baseline.quality
    if quality is None or quality.slices is None:
        return 0.0
    group_summary = quality.slices.group.get(group)
    if group_summary is None:
        return 0.0
    return float(getattr(group_summary, metric))


def _latency_ratio(candidate: BaselineResult, control: BaselineResult) -> float:
    candidate_p95 = _baseline_p95(candidate)
    control_p95 = _baseline_p95(control)
    if control_p95 <= 0.0:
        return 1.0 if candidate_p95 <= 0.0 else float("inf")
    return round(candidate_p95 / control_p95, 6)


def _baseline_p95(baseline: BaselineResult) -> float:
    latency = baseline.latency
    if latency is None:
        return 0.0
    return float(latency.p95_ms)


def _has_usable_operational_evidence(entry: CandidateMatrixEntry) -> bool:
    evidence = entry.operational_evidence
    if evidence is None:
        return False
    return (
        evidence.memory_evidence_status == "measured"
        and evidence.disk_size_evidence_status == "measured"
    )
