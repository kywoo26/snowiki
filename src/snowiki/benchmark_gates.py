from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True, slots=True)
class AnalyzerPromotionGate:
    gate_id: str
    baseline_target: str
    candidate_targets: tuple[str, ...]
    required_dataset_ids: tuple[str, ...]
    required_level_ids: tuple[str, ...]
    required_slice_ids: tuple[str, ...]
    required_golden_query_ids: tuple[str, ...]
    thresholds: dict[str, object]


@dataclass(frozen=True, slots=True)
class GateCheckResult:
    check_id: str
    candidate_target: str
    status: str
    message: str
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class GateCandidateResult:
    target_id: str
    status: str
    checks: tuple[GateCheckResult, ...]


@dataclass(frozen=True, slots=True)
class GateEvaluationResult:
    gate_id: str
    baseline_target: str
    status: str
    candidates: tuple[GateCandidateResult, ...]
    failures: tuple[str, ...]


def load_analyzer_promotion_gate(path: str | Path) -> AnalyzerPromotionGate:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    raw_payload: object = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Expected analyzer gate mapping at {source_path}")
    payload = {str(key): value for key, value in raw_payload.items()}
    public_matrix = _require_mapping(payload, "public_matrix", source_path)
    snowiki_slices = _require_mapping(payload, "snowiki_slices", source_path)
    return AnalyzerPromotionGate(
        gate_id=_require_str(payload, "gate_id", source_path),
        baseline_target=_require_str(payload, "baseline_target", source_path),
        candidate_targets=tuple(_require_str_list(payload, "candidate_targets", source_path)),
        required_dataset_ids=tuple(
            _require_str_list(public_matrix, "required_dataset_ids", source_path)
        ),
        required_level_ids=tuple(
            _require_str_list(public_matrix, "required_level_ids", source_path)
        ),
        required_slice_ids=tuple(
            _require_str_list(snowiki_slices, "required_slice_ids", source_path)
        ),
        required_golden_query_ids=tuple(
            _require_str_list(snowiki_slices, "required_golden_query_ids", source_path)
        ),
        thresholds=_require_mapping(payload, "thresholds", source_path),
    )


def load_benchmark_report(path: str | Path) -> dict[str, object]:
    source_path = Path(path)
    raw_payload: object = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError(f"Expected benchmark report mapping at {source_path}")
    return {str(key): value for key, value in raw_payload.items()}


def evaluate_analyzer_promotion_gate(
    *,
    gate: AnalyzerPromotionGate,
    report: dict[str, object],
) -> GateEvaluationResult:
    cells = _successful_cells(report)
    candidates: list[GateCandidateResult] = []
    failures: list[str] = []
    for candidate_target in gate.candidate_targets:
        checks = (
            *_evaluate_required_public_cells(gate, cells, candidate_target),
            *_evaluate_public_korean(gate, cells, candidate_target),
            *_evaluate_public_english(gate, cells, candidate_target),
            *_evaluate_latency(gate, cells, candidate_target),
            *_evaluate_required_slices(gate, cells, candidate_target),
            *_evaluate_snowiki_korean(gate, cells, candidate_target),
            *_evaluate_slice_regressions(gate, cells, candidate_target),
            *_evaluate_golden_queries(gate, cells, candidate_target),
        )
        candidate_failures = tuple(check for check in checks if check.status != "pass")
        status = "pass" if not candidate_failures else "fail"
        failures.extend(check.message for check in candidate_failures)
        candidates.append(
            GateCandidateResult(
                target_id=candidate_target,
                status=status,
                checks=checks,
            )
        )
    return GateEvaluationResult(
        gate_id=gate.gate_id,
        baseline_target=gate.baseline_target,
        status="pass" if not failures else "fail",
        candidates=tuple(candidates),
        failures=tuple(failures),
    )


def render_gate_json(result: GateEvaluationResult) -> dict[str, object]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "gate_id": result.gate_id,
        "baseline_target": result.baseline_target,
        "summary": {
            "candidate_count": len(result.candidates),
            "pass_count": sum(1 for candidate in result.candidates if candidate.status == "pass"),
            "fail_count": sum(1 for candidate in result.candidates if candidate.status == "fail"),
            "failure_count": len(result.failures),
        },
        "status": result.status,
        "candidates": [
            {
                "target_id": candidate.target_id,
                "status": candidate.status,
                "checks": [
                    {
                        "check_id": check.check_id,
                        "status": check.status,
                        "message": check.message,
                        "details": check.details,
                    }
                    for check in candidate.checks
                ],
            }
            for candidate in result.candidates
        ],
        "failures": list(result.failures),
    }


def render_gate_summary(result: GateEvaluationResult) -> str:
    return (
        f"gate={result.gate_id} candidates={len(result.candidates)} "
        f"status={result.status} failures={len(result.failures)}"
    )


def _evaluate_required_public_cells(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    missing: list[str] = []
    for dataset_id in gate.required_dataset_ids:
        for level_id in gate.required_level_ids:
            if _find_cell(cells, dataset_id, level_id, gate.baseline_target) is None:
                missing.append(f"{dataset_id}/{level_id}/{gate.baseline_target}")
            if _find_cell(cells, dataset_id, level_id, candidate_target) is None:
                missing.append(f"{dataset_id}/{level_id}/{candidate_target}")
    if missing:
        return (
            _check(
                "required_public_cells",
                candidate_target,
                "fail",
                f"{candidate_target} is missing required public cells: {', '.join(missing)}",
                {"missing_cells": missing},
            ),
        )
    return (
        _check(
            "required_public_cells",
            candidate_target,
            "pass",
            f"{candidate_target} includes all required public cells",
            {},
        ),
    )


def _evaluate_public_korean(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    threshold = _threshold_mapping(gate, "public_korean")
    dataset_id = _mapping_str(threshold, "dataset_id")
    slice_id = _mapping_str(threshold, "slice_id")
    metrics = _mapping_mapping(threshold, "must_improve_metrics")
    return tuple(
        _evaluate_relative_improvement(
            cells,
            check_id=f"public_korean:{metric_id}",
            candidate_target=candidate_target,
            baseline_target=gate.baseline_target,
            dataset_id=dataset_id,
            level_ids=gate.required_level_ids,
            slice_id=slice_id,
            metric_id=metric_id,
            min_relative_delta=_mapping_float(_as_mapping(raw_rule), "min_relative_delta"),
        )
        for metric_id, raw_rule in metrics.items()
    )


def _evaluate_public_english(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    threshold = gate.thresholds.get("public_english_regression")
    if not isinstance(threshold, dict):
        return ()
    threshold_mapping = {str(key): value for key, value in threshold.items()}
    dataset_ids = tuple(_mapping_str_list(threshold_mapping, "dataset_ids"))
    metrics = tuple(_mapping_str_list(threshold_mapping, "metrics"))
    max_abs = _mapping_float(threshold_mapping, "max_allowed_absolute_regression")
    max_rel = _mapping_float(threshold_mapping, "max_allowed_relative_regression")
    checks: list[GateCheckResult] = []
    for dataset_id in dataset_ids:
        for metric_id in metrics:
            checks.append(
                _evaluate_regression(
                    cells,
                    check_id=f"public_english:{dataset_id}:{metric_id}",
                    candidate_target=candidate_target,
                    baseline_target=gate.baseline_target,
                    dataset_id=dataset_id,
                    level_ids=gate.required_level_ids,
                    slice_id="all",
                    metric_id=metric_id,
                    max_absolute_regression=max_abs,
                    max_relative_regression=max_rel,
                )
            )
    return tuple(checks)


def _evaluate_latency(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    threshold = _threshold_mapping(gate, "latency")
    max_multiplier = _mapping_float(threshold, "max_p95_multiplier_vs_baseline")
    checks: list[GateCheckResult] = []
    for dataset_id in gate.required_dataset_ids:
        for level_id in gate.required_level_ids:
            baseline = _find_cell(cells, dataset_id, level_id, gate.baseline_target)
            candidate = _find_cell(cells, dataset_id, level_id, candidate_target)
            if baseline is None or candidate is None:
                checks.append(
                    _check(
                        f"latency:{dataset_id}:{level_id}",
                        candidate_target,
                        "fail",
                        f"{candidate_target} is missing latency evidence for {dataset_id}/{level_id}",
                        {"dataset_id": dataset_id, "level_id": level_id},
                    )
                )
                continue
            baseline_value = _latency_p95(baseline)
            candidate_value = _latency_p95(candidate)
            if baseline_value is None or candidate_value is None or baseline_value <= 0.0:
                checks.append(
                    _check(
                        f"latency:{dataset_id}:{level_id}",
                        candidate_target,
                        "fail",
                        f"{candidate_target} has incomplete latency evidence for {dataset_id}/{level_id}",
                        {
                            "dataset_id": dataset_id,
                            "level_id": level_id,
                            "baseline_p95_ms": baseline_value,
                            "candidate_p95_ms": candidate_value,
                        },
                    )
                )
                continue
            multiplier = candidate_value / baseline_value
            status = "pass" if multiplier <= max_multiplier else "fail"
            checks.append(
                _check(
                    f"latency:{dataset_id}:{level_id}",
                    candidate_target,
                    status,
                    (
                        f"{candidate_target} p95 latency multiplier on {dataset_id}/{level_id} "
                        f"is {multiplier:.4f} (max {max_multiplier:.4f})"
                    ),
                    {
                        "dataset_id": dataset_id,
                        "level_id": level_id,
                        "baseline_p95_ms": baseline_value,
                        "candidate_p95_ms": candidate_value,
                        "multiplier": multiplier,
                        "max_multiplier": max_multiplier,
                    },
                )
            )
    return tuple(checks)


def _evaluate_required_slices(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    missing: list[dict[str, object]] = []
    for slice_id in gate.required_slice_ids:
        pairs, missing_pairs = _slice_pairs(
            cells,
            gate.baseline_target,
            candidate_target,
            slice_id,
        )
        if not pairs and not missing_pairs:
            missing.append({"slice_id": slice_id, "reason": "missing_baseline_slice"})
            continue
        for dataset_id, level_id in missing_pairs:
            missing.append(
                {
                    "slice_id": slice_id,
                    "dataset_id": dataset_id,
                    "level_id": level_id,
                    "reason": "missing_candidate_slice",
                }
            )
    if missing:
        return (
            _check(
                "required_snowiki_slices",
                candidate_target,
                "fail",
                f"{candidate_target} is missing Snowiki slice evidence",
                {"missing_slices": missing},
            ),
        )
    return (
        _check(
            "required_snowiki_slices",
            candidate_target,
            "pass",
            f"{candidate_target} includes all required Snowiki slice evidence",
            {},
        ),
    )


def _evaluate_snowiki_korean(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    threshold = _threshold_mapping(gate, "snowiki_korean")
    slice_id = _mapping_str(threshold, "slice_id")
    metrics = _mapping_mapping(threshold, "must_improve_metrics")
    return tuple(
        _evaluate_slice_relative_improvement(
            cells,
            check_id=f"snowiki_korean:{metric_id}",
            candidate_target=candidate_target,
            baseline_target=gate.baseline_target,
            slice_id=slice_id,
            metric_id=metric_id,
            min_relative_delta=_mapping_float(_as_mapping(raw_rule), "min_relative_delta"),
        )
        for metric_id, raw_rule in metrics.items()
    )


def _evaluate_slice_regressions(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    checks: list[GateCheckResult] = []
    for threshold_id in (
        "mixed_and_identifier_regression",
        "temporal_regression",
        "english_regression",
    ):
        threshold = _threshold_mapping(gate, threshold_id)
        slice_ids = _threshold_slice_ids(threshold)
        metrics = tuple(_mapping_str_list(threshold, "metrics"))
        max_abs = _mapping_float(threshold, "max_allowed_absolute_regression")
        max_rel = _optional_mapping_float(
            threshold,
            "max_allowed_relative_regression",
            default=1.0,
        )
        for slice_id in slice_ids:
            for metric_id in metrics:
                checks.append(
                    _evaluate_slice_regression(
                        cells,
                        check_id=f"{threshold_id}:{slice_id}:{metric_id}",
                        candidate_target=candidate_target,
                        baseline_target=gate.baseline_target,
                        slice_id=slice_id,
                        metric_id=metric_id,
                        max_absolute_regression=max_abs,
                        max_relative_regression=max_rel,
                    )
                )
    return tuple(checks)


def _evaluate_golden_queries(
    gate: AnalyzerPromotionGate,
    cells: tuple[dict[str, object], ...],
    candidate_target: str,
) -> tuple[GateCheckResult, ...]:
    threshold = _threshold_mapping(gate, "golden_query_regression")
    max_regressions = _optional_mapping_int(
        threshold,
        "max_allowed_top5_regressions",
        default=0,
    )
    threshold_query_ids = tuple(_mapping_str_list(threshold, "required_query_ids"))
    required_query_ids = tuple(dict.fromkeys((*gate.required_golden_query_ids, *threshold_query_ids)))
    regressions: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    for query_id in required_query_ids:
        baseline_cells = tuple(
            cell
            for cell in cells
            if cell.get("target_id") == gate.baseline_target
            and _per_query_metric(cell, query_id, "hit_rate_at_5") is not None
        )
        if not baseline_cells:
            missing.append({"query_id": query_id, "reason": "missing_baseline_query"})
            continue
        for baseline in baseline_cells:
            dataset_id = str(baseline.get("dataset_id", ""))
            level_id = str(baseline.get("level_id", ""))
            candidate = _find_cell(cells, dataset_id, level_id, candidate_target)
            baseline_hit = _per_query_metric(baseline, query_id, "hit_rate_at_5")
            candidate_hit = (
                _per_query_metric(candidate, query_id, "hit_rate_at_5")
                if candidate is not None
                else None
            )
            if baseline_hit is None or candidate_hit is None:
                missing.append(
                    {
                        "query_id": query_id,
                        "dataset_id": dataset_id,
                        "level_id": level_id,
                        "reason": "missing_candidate_query",
                    }
                )
                continue
            if candidate_hit < baseline_hit:
                regressions.append(
                    {
                        "query_id": query_id,
                        "dataset_id": dataset_id,
                        "level_id": level_id,
                        "baseline_hit_rate_at_5": baseline_hit,
                        "candidate_hit_rate_at_5": candidate_hit,
                    }
                )
    if missing:
        return (
            _check(
                "golden_query_regression",
                candidate_target,
                "fail",
                f"{candidate_target} is missing golden query evidence",
                {"missing_evidence": missing},
            ),
        )
    status = "pass" if len(regressions) <= max_regressions else "fail"
    return (
        _check(
            "golden_query_regression",
            candidate_target,
            status,
            (
                f"{candidate_target} has {len(regressions)} top-5 golden query regressions "
                f"(max {max_regressions})"
            ),
            {
                "regressions": regressions,
                "required_query_ids": list(required_query_ids),
                "max_allowed_top5_regressions": max_regressions,
            },
        ),
    )


def _evaluate_relative_improvement(
    cells: tuple[dict[str, object], ...],
    *,
    check_id: str,
    candidate_target: str,
    baseline_target: str,
    dataset_id: str,
    level_ids: tuple[str, ...],
    slice_id: str,
    metric_id: str,
    min_relative_delta: float,
) -> GateCheckResult:
    for level_id in level_ids:
        baseline = _find_cell(cells, dataset_id, level_id, baseline_target)
        candidate = _find_cell(cells, dataset_id, level_id, candidate_target)
        if baseline is None or candidate is None:
            continue
        baseline_value = _metric_value(baseline, metric_id, slice_id)
        candidate_value = _metric_value(candidate, metric_id, slice_id)
        if baseline_value is None or candidate_value is None:
            continue
        relative_delta = _relative_delta(candidate_value, baseline_value)
        status = "pass" if relative_delta >= min_relative_delta else "fail"
        return _check(
            check_id,
            candidate_target,
            status,
            (
                f"{candidate_target} {metric_id} relative delta on {dataset_id}/{level_id}/{slice_id} "
                f"is {relative_delta:.4f} (min {min_relative_delta:.4f})"
            ),
            {
                "dataset_id": dataset_id,
                "level_id": level_id,
                "slice_id": slice_id,
                "metric_id": metric_id,
                "baseline_value": baseline_value,
                "candidate_value": candidate_value,
                "relative_delta": relative_delta,
                "min_relative_delta": min_relative_delta,
            },
        )
    return _missing_metric_check(check_id, candidate_target, dataset_id, slice_id, metric_id)


def _evaluate_slice_relative_improvement(
    cells: tuple[dict[str, object], ...],
    *,
    check_id: str,
    candidate_target: str,
    baseline_target: str,
    slice_id: str,
    metric_id: str,
    min_relative_delta: float,
) -> GateCheckResult:
    pairs, missing_pairs = _slice_pairs(cells, baseline_target, candidate_target, slice_id)
    failures: list[dict[str, object]] = []
    if not pairs:
        return _missing_metric_check(check_id, candidate_target, "snowiki", slice_id, metric_id)
    for baseline, candidate in pairs:
        baseline_value = _metric_value(baseline, metric_id, slice_id)
        candidate_value = _metric_value(candidate, metric_id, slice_id)
        dataset_id = str(candidate.get("dataset_id", "unknown"))
        level_id = str(candidate.get("level_id", "unknown"))
        if baseline_value is None or candidate_value is None:
            failures.append({"dataset_id": dataset_id, "level_id": level_id, "reason": "missing_metric"})
            continue
        relative_delta = _relative_delta(candidate_value, baseline_value)
        if relative_delta < min_relative_delta:
            failures.append(
                {
                    "dataset_id": dataset_id,
                    "level_id": level_id,
                    "baseline_value": baseline_value,
                    "candidate_value": candidate_value,
                    "relative_delta": relative_delta,
                }
            )
    for dataset_id, level_id in missing_pairs:
        failures.append({"dataset_id": dataset_id, "level_id": level_id, "reason": "missing_candidate_slice"})
    status = "pass" if not failures else "fail"
    return _check(
        check_id,
        candidate_target,
        status,
        (
            f"{candidate_target} {metric_id} relative delta on {slice_id} "
            f"failed {len(failures)} of {len(pairs) + len(missing_pairs)} scoped comparisons "
            f"(min {min_relative_delta:.4f})"
        ),
        {
            "slice_id": slice_id,
            "metric_id": metric_id,
            "comparison_count": len(pairs),
            "missing_candidate_slice_count": len(missing_pairs),
            "min_relative_delta": min_relative_delta,
            "failures": failures,
        },
    )


def _evaluate_regression(
    cells: tuple[dict[str, object], ...],
    *,
    check_id: str,
    candidate_target: str,
    baseline_target: str,
    dataset_id: str,
    level_ids: tuple[str, ...],
    slice_id: str,
    metric_id: str,
    max_absolute_regression: float,
    max_relative_regression: float,
) -> GateCheckResult:
    for level_id in level_ids:
        baseline = _find_cell(cells, dataset_id, level_id, baseline_target)
        candidate = _find_cell(cells, dataset_id, level_id, candidate_target)
        if baseline is None or candidate is None:
            continue
        return _compare_regression(
            check_id=check_id,
            candidate_target=candidate_target,
            baseline=baseline,
            candidate=candidate,
            slice_id=slice_id,
            metric_id=metric_id,
            max_absolute_regression=max_absolute_regression,
            max_relative_regression=max_relative_regression,
        )
    return _missing_metric_check(check_id, candidate_target, dataset_id, slice_id, metric_id)


def _evaluate_slice_regression(
    cells: tuple[dict[str, object], ...],
    *,
    check_id: str,
    candidate_target: str,
    baseline_target: str,
    slice_id: str,
    metric_id: str,
    max_absolute_regression: float,
    max_relative_regression: float,
) -> GateCheckResult:
    pairs, missing_pairs = _slice_pairs(cells, baseline_target, candidate_target, slice_id)
    if not pairs:
        return _missing_metric_check(check_id, candidate_target, "snowiki", slice_id, metric_id)
    failures: list[dict[str, object]] = []
    for baseline, candidate in pairs:
        baseline_value = _metric_value(baseline, metric_id, slice_id)
        candidate_value = _metric_value(candidate, metric_id, slice_id)
        dataset_id = str(candidate.get("dataset_id", "unknown"))
        level_id = str(candidate.get("level_id", "unknown"))
        if baseline_value is None or candidate_value is None:
            failures.append({"dataset_id": dataset_id, "level_id": level_id, "reason": "missing_metric"})
            continue
        absolute_regression = max(0.0, baseline_value - candidate_value)
        relative_regression = absolute_regression / baseline_value if baseline_value > 0.0 else 0.0
        if absolute_regression > max_absolute_regression or relative_regression > max_relative_regression:
            failures.append(
                {
                    "dataset_id": dataset_id,
                    "level_id": level_id,
                    "baseline_value": baseline_value,
                    "candidate_value": candidate_value,
                    "absolute_regression": absolute_regression,
                    "relative_regression": relative_regression,
                }
            )
    for dataset_id, level_id in missing_pairs:
        failures.append({"dataset_id": dataset_id, "level_id": level_id, "reason": "missing_candidate_slice"})
    status = "pass" if not failures else "fail"
    return _check(
        check_id,
        candidate_target,
        status,
        (
            f"{candidate_target} {metric_id} regression on {slice_id} "
            f"failed {len(failures)} of {len(pairs) + len(missing_pairs)} scoped comparisons "
            f"(max abs={max_absolute_regression:.4f}, max rel={max_relative_regression:.4f})"
        ),
        {
            "slice_id": slice_id,
            "metric_id": metric_id,
            "comparison_count": len(pairs),
            "missing_candidate_slice_count": len(missing_pairs),
            "max_absolute_regression": max_absolute_regression,
            "max_relative_regression": max_relative_regression,
            "failures": failures,
        },
    )


def _compare_regression(
    *,
    check_id: str,
    candidate_target: str,
    baseline: dict[str, object],
    candidate: dict[str, object],
    slice_id: str,
    metric_id: str,
    max_absolute_regression: float,
    max_relative_regression: float,
) -> GateCheckResult:
    baseline_value = _metric_value(baseline, metric_id, slice_id)
    candidate_value = _metric_value(candidate, metric_id, slice_id)
    if baseline_value is None or candidate_value is None:
        dataset_id = str(candidate.get("dataset_id", "unknown"))
        return _missing_metric_check(check_id, candidate_target, dataset_id, slice_id, metric_id)
    absolute_regression = max(0.0, baseline_value - candidate_value)
    relative_regression = absolute_regression / baseline_value if baseline_value > 0.0 else 0.0
    status = (
        "pass"
        if absolute_regression <= max_absolute_regression
        and relative_regression <= max_relative_regression
        else "fail"
    )
    dataset_id = str(candidate.get("dataset_id", "unknown"))
    level_id = str(candidate.get("level_id", "unknown"))
    return _check(
        check_id,
        candidate_target,
        status,
        (
            f"{candidate_target} {metric_id} regression on {dataset_id}/{level_id}/{slice_id} "
            f"is abs={absolute_regression:.4f}, rel={relative_regression:.4f} "
            f"(max abs={max_absolute_regression:.4f}, max rel={max_relative_regression:.4f})"
        ),
        {
            "dataset_id": dataset_id,
            "level_id": level_id,
            "slice_id": slice_id,
            "metric_id": metric_id,
            "baseline_value": baseline_value,
            "candidate_value": candidate_value,
            "absolute_regression": absolute_regression,
            "relative_regression": relative_regression,
            "max_absolute_regression": max_absolute_regression,
            "max_relative_regression": max_relative_regression,
        },
    )


def _successful_cells(report: dict[str, object]) -> tuple[dict[str, object], ...]:
    raw_cells = report.get("cells")
    if not isinstance(raw_cells, list):
        raise ValueError("Benchmark report must include a cells list.")
    cells: list[dict[str, object]] = []
    for raw_cell in raw_cells:
        if not isinstance(raw_cell, dict):
            continue
        cell = {str(key): value for key, value in raw_cell.items()}
        if cell.get("status") == "success":
            cells.append(cell)
    return tuple(cells)


def _find_cell(
    cells: tuple[dict[str, object], ...],
    dataset_id: str,
    level_id: str,
    target_id: str,
) -> dict[str, object] | None:
    for cell in cells:
        if (
            cell.get("dataset_id") == dataset_id
            and cell.get("level_id") == level_id
            and cell.get("target_id") == target_id
        ):
            return cell
    return None


def _slice_pairs(
    cells: tuple[dict[str, object], ...],
    baseline_target: str,
    candidate_target: str,
    slice_id: str,
) -> tuple[tuple[tuple[dict[str, object], dict[str, object]], ...], tuple[tuple[str, str], ...]]:
    pairs: list[tuple[dict[str, object], dict[str, object]]] = []
    missing_candidate_slices: list[tuple[str, str]] = []
    for baseline in cells:
        if baseline.get("target_id") != baseline_target or not _cell_slice(baseline, slice_id):
            continue
        dataset_id = str(baseline.get("dataset_id", ""))
        level_id = str(baseline.get("level_id", ""))
        candidate = _find_cell(cells, dataset_id, level_id, candidate_target)
        if candidate is None or not _cell_slice(candidate, slice_id):
            missing_candidate_slices.append((dataset_id, level_id))
            continue
        pairs.append((baseline, candidate))
    return tuple(pairs), tuple(missing_candidate_slices)


def _metric_value(cell: dict[str, object], metric_id: str, slice_id: str) -> float | None:
    if slice_id != "all":
        slice_payload = _cell_slice(cell, slice_id)
        if not slice_payload:
            return None
        metrics = _object_mapping(slice_payload.get("metrics"))
        if metrics is None:
            return None
        return _float_or_none(metrics.get(metric_id))
    slice_payload = _cell_slice(cell, "all")
    if slice_payload:
        metrics = _object_mapping(slice_payload.get("metrics"))
        if metrics is not None:
            value = _float_or_none(metrics.get(metric_id))
            if value is not None:
                return value
    raw_metrics = cell.get("metrics")
    if not isinstance(raw_metrics, list):
        return None
    for raw_metric in raw_metrics:
        if not isinstance(raw_metric, dict):
            continue
        metric = {str(key): value for key, value in raw_metric.items()}
        if metric.get("metric_id") == metric_id:
            return _float_or_none(metric.get("value"))
    return None


def _latency_p95(cell: dict[str, object]) -> float | None:
    latency = _object_mapping(cell.get("latency"))
    if latency is None:
        return None
    return _float_or_none(latency.get("p95"))


def _cell_slice(cell: dict[str, object], slice_id: str) -> dict[str, object] | None:
    slices = _object_mapping(cell.get("slices"))
    if slices is None:
        return None
    return _object_mapping(slices.get(slice_id))


def _per_query_metric(
    cell: dict[str, object],
    query_id: str,
    metric_id: str,
) -> float | None:
    per_query = _object_mapping(cell.get("per_query"))
    if per_query is None:
        return None
    raw_query = _object_mapping(per_query.get(query_id))
    if raw_query is None:
        return None
    metrics = _object_mapping(raw_query.get("metrics"))
    if metrics is None:
        return None
    return _float_or_none(metrics.get(metric_id))


def _object_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _threshold_mapping(gate: AnalyzerPromotionGate, key: str) -> dict[str, object]:
    return _as_mapping(gate.thresholds.get(key))


def _threshold_slice_ids(threshold: dict[str, object]) -> tuple[str, ...]:
    if "slice_ids" in threshold:
        return tuple(_mapping_str_list(threshold, "slice_ids"))
    return (_mapping_str(threshold, "slice_id"),)


def _check(
    check_id: str,
    candidate_target: str,
    status: str,
    message: str,
    details: dict[str, object],
) -> GateCheckResult:
    return GateCheckResult(
        check_id=check_id,
        candidate_target=candidate_target,
        status=status,
        message=message,
        details=details,
    )


def _missing_metric_check(
    check_id: str,
    candidate_target: str,
    dataset_id: str,
    slice_id: str,
    metric_id: str,
) -> GateCheckResult:
    return _check(
        check_id,
        candidate_target,
        "fail",
        f"{candidate_target} is missing {metric_id} evidence for {dataset_id}/{slice_id}",
        {"dataset_id": dataset_id, "slice_id": slice_id, "metric_id": metric_id},
    )


def _relative_delta(candidate_value: float, baseline_value: float) -> float:
    if baseline_value == 0.0:
        return 0.0 if candidate_value == 0.0 else 1.0
    return (candidate_value - baseline_value) / baseline_value


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _require_mapping(
    payload: dict[str, object],
    key: str,
    source_path: Path,
) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {key!r} in {source_path}")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _require_str(payload: dict[str, object], key: str, source_path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key!r} in {source_path}")
    return value


def _require_str_list(
    payload: dict[str, object],
    key: str,
    source_path: Path,
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Expected list[str] for {key!r} in {source_path}")
    return cast(list[str], value)


def _as_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _mapping_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {key!r}")
    return {str(item_key): item_value for item_key, item_value in value.items()}


def _mapping_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Expected string for {key!r}")
    return value


def _mapping_str_list(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Expected list[str] for {key!r}")
    return cast(list[str], value)


def _optional_mapping_float(
    payload: dict[str, object],
    key: str,
    *,
    default: float,
) -> float:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Expected number for {key!r}")
    return float(value)


def _optional_mapping_int(
    payload: dict[str, object],
    key: str,
    *,
    default: int,
) -> int:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected integer for {key!r}")
    return value


def _mapping_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Expected number for {key!r}")
    return float(value)
