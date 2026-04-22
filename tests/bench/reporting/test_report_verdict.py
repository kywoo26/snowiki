from __future__ import annotations

from importlib import import_module


def _baseline_payload_for_verdict(
    *,
    name: str,
    mixed_value: float = 0.9,
    ko_value: float = 0.9,
    en_value: float = 0.9,
    p95_ms: float = 10.0,
    overall_fail: bool = False,
    include_overall_threshold: bool = True,
) -> dict[str, object]:
    thresholds: list[dict[str, object]] = []
    if include_overall_threshold:
        thresholds.append(
            {
                "gate": "overall",
                "metric": "mrr",
                "value": mixed_value,
                "delta": mixed_value - 0.7,
                "verdict": "FAIL" if overall_fail else "PASS",
                "threshold": 0.7,
                "warnings": [],
            }
        )

    def _group_payload(value: float) -> dict[str, object]:
        return {
            "recall_at_k": value,
            "mrr": value,
            "ndcg_at_k": value,
            "top_k": 5,
            "queries_evaluated": 1,
            "per_query": [],
        }

    return {
        "name": name,
        "latency": {
            "p50_ms": min(p95_ms, 5.0),
            "p95_ms": p95_ms,
            "mean_ms": p95_ms,
            "min_ms": min(p95_ms, 5.0),
            "max_ms": p95_ms,
        },
        "quality": {
            "overall": {
                "recall_at_k": mixed_value,
                "mrr": mixed_value,
                "ndcg_at_k": mixed_value,
                "top_k": 5,
                "queries_evaluated": 1,
                "per_query": [],
            },
            "slices": {
                "group": {
                    "mixed": _group_payload(mixed_value),
                    "ko": _group_payload(ko_value),
                    "en": _group_payload(en_value),
                },
                "kind": {},
            },
            "thresholds": thresholds,
        },
        "queries": [],
    }


def _operational_evidence_payload(*, measured: bool) -> dict[str, object]:
    status = "measured" if measured else "not_measured"
    return {
        "memory_peak_rss_mb": 1.0 if measured else None,
        "memory_evidence_status": status,
        "disk_size_mb": 1.0 if measured else None,
        "disk_size_evidence_status": status,
        "platform_support": {
            "macos": "supported",
            "linux_x86_64": "supported",
            "linux_aarch64": "supported",
            "windows": "supported",
            "fallback_behavior": "none",
        },
        "install_ergonomics": {
            "prebuilt_available": True,
            "build_from_source_required": False,
            "hidden_bootstrap_steps": False,
            "operational_complexity": "low",
        },
        "zero_cost_admission": True,
        "admission_reason": "test",
    }



def _baseline_payload_for_verdict(
    *,
    name: str,
    mixed_value: float = 0.9,
    ko_value: float = 0.9,
    en_value: float = 0.9,
    p95_ms: float = 10.0,
    overall_fail: bool = False,
    include_overall_threshold: bool = True,
) -> dict[str, object]:
    thresholds: list[dict[str, object]] = []
    if include_overall_threshold:
        thresholds.append(
            {
                "gate": "overall",
                "metric": "mrr",
                "value": mixed_value,
                "delta": mixed_value - 0.7,
                "verdict": "FAIL" if overall_fail else "PASS",
                "threshold": 0.7,
                "warnings": [],
            }
        )

    def _group_payload(value: float) -> dict[str, object]:
        return {
            "recall_at_k": value,
            "mrr": value,
            "ndcg_at_k": value,
            "top_k": 5,
            "queries_evaluated": 1,
            "per_query": [],
        }

    return {
        "name": name,
        "latency": {
            "p50_ms": min(p95_ms, 5.0),
            "p95_ms": p95_ms,
            "mean_ms": p95_ms,
            "min_ms": min(p95_ms, 5.0),
            "max_ms": p95_ms,
        },
        "quality": {
            "overall": {
                "recall_at_k": mixed_value,
                "mrr": mixed_value,
                "ndcg_at_k": mixed_value,
                "top_k": 5,
                "queries_evaluated": 1,
                "per_query": [],
            },
            "slices": {
                "group": {
                    "mixed": _group_payload(mixed_value),
                    "ko": _group_payload(ko_value),
                    "en": _group_payload(en_value),
                },
                "kind": {},
            },
            "thresholds": thresholds,
        },
        "queries": [],
    }


def _operational_evidence_payload(*, measured: bool) -> dict[str, object]:
    status = "measured" if measured else "not_measured"
    return {
        "memory_peak_rss_mb": 1.0 if measured else None,
        "memory_evidence_status": status,
        "disk_size_mb": 1.0 if measured else None,
        "disk_size_evidence_status": status,
        "platform_support": {
            "macos": "supported",
            "linux_x86_64": "supported",
            "linux_aarch64": "supported",
            "windows": "supported",
            "fallback_behavior": "none",
        },
        "install_ergonomics": {
            "prebuilt_available": True,
            "build_from_source_required": False,
            "hidden_bootstrap_steps": False,
            "operational_complexity": "low",
        },
        "zero_cost_admission": True,
        "admission_reason": "test",
    }


def test_verdict_internal_helpers_cover_edge_cases() -> None:
    verdict = import_module("snowiki.bench.reporting.verdict")
    models = import_module("snowiki.bench.reporting.models")

    assert verdict._report_tier({"metadata": {"dataset_tier": "official_suite"}}) == "official_suite"
    assert verdict._report_tier({"dataset": {"tier": "official_suite"}}) == "official_suite"
    assert verdict._report_tier({}) == "regression_harness"

    assert verdict.performance_threshold_failure_count({"performance_thresholds": "bad"}) == 0
    assert verdict.retrieval_threshold_failure_count({"retrieval": {"baselines": "bad"}}) == 0
    assert verdict.benchmark_exit_code({"benchmark_verdict": {"exit_code": True}}) == 1
    assert verdict.benchmark_exit_code({"benchmark_verdict": {"exit_code": 2}}) == 2
    assert verdict.benchmark_exit_code({}) == 0

    missing_control = verdict._control_decision(None)
    assert missing_control.reasons == ["missing_control_evidence"]

    control_without_measurements = verdict._control_decision(
        models.CandidateMatrixEntry.model_validate(
            {
                "candidate_name": "regex_v1",
                "evidence_baseline": "lexical",
                "role": "control",
                "admission_status": "admitted",
                "control": True,
                "operational_evidence": _operational_evidence_payload(measured=False),
                "baseline": _baseline_payload_for_verdict(name="lexical"),
            }
        )
    )
    assert control_without_measurements.disposition == "benchmark_only"
    assert control_without_measurements.reasons == ["missing_operational_evidence"]

    control_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "regex_v1",
            "evidence_baseline": "lexical",
            "role": "control",
            "admission_status": "admitted",
            "control": True,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="lexical",
                mixed_value=0.80,
                ko_value=0.80,
                en_value=0.80,
                p95_ms=10.0,
            ),
        }
    )

    assert verdict._candidate_decision(
        None,
        control_entry,
        verdict.CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["missing_benchmark_evidence"]

    overall_fail_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.85,
                ko_value=0.85,
                en_value=0.85,
                p95_ms=11.0,
                overall_fail=True,
            ),
        }
    )
    assert verdict._candidate_decision(
        overall_fail_entry,
        control_entry,
        verdict.CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["overall_quality_gate_failed"]

    no_improvement_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=True),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.80,
                ko_value=0.80,
                en_value=0.80,
                p95_ms=10.0,
            ),
        }
    )
    assert verdict._candidate_decision(
        no_improvement_entry,
        control_entry,
        verdict.CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    ).reasons == ["no_material_mixed_improvement"]

    benchmark_only_entry = models.CandidateMatrixEntry.model_validate(
        {
            "candidate_name": "kiwi_morphology_v1",
            "evidence_baseline": "bm25s_kiwi_full",
            "role": "candidate",
            "admission_status": "admitted",
            "control": False,
            "operational_evidence": _operational_evidence_payload(measured=False),
            "baseline": _baseline_payload_for_verdict(
                name="bm25s_kiwi_full",
                mixed_value=0.81,
                ko_value=0.78,
                en_value=0.78,
                p95_ms=15.0,
            ),
        }
    )
    benchmark_only = verdict._candidate_decision(
        benchmark_only_entry,
        control_entry,
        verdict.CANDIDATE_POLICY["thresholds"],
        candidate_name="kiwi_morphology_v1",
        evidence_baseline="bm25s_kiwi_full",
    )
    assert benchmark_only.disposition == "benchmark_only"
    assert benchmark_only.reasons == [
        "mixed_delta_below_promotion_threshold",
        "slice_recall_non_regression_failed",
        "latency_ratio_guard_failed",
        "missing_operational_evidence",
    ]

    baseline_without_overall = models.BaselineResult.model_validate(
        _baseline_payload_for_verdict(
            name="lexical",
            include_overall_threshold=False,
        )
    )
    assert verdict._passes_overall_quality_gates(baseline_without_overall) is False
    assert verdict._group_metric(baseline_without_overall, "missing", "mrr") == 0.0
    assert verdict._latency_ratio(
        models.BaselineResult.model_validate(
            _baseline_payload_for_verdict(name="candidate", p95_ms=5.0)
        ),
        models.BaselineResult.model_validate(
            _baseline_payload_for_verdict(name="control", p95_ms=0.0)
        ),
    ) == float("inf")
    assert verdict._baseline_p95(
        models.BaselineResult.model_validate({"name": "empty", "queries": []})
    ) == 0.0
