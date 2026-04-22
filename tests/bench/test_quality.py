from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any

from snowiki.bench.reporting.models import (
    BaselineResult,
    CandidateMatrixEntry,
    CandidateMatrixReport,
    CandidateOperationalEvidence,
    InstallErgonomicsEvidence,
    PlatformSupportEvidence,
)
from snowiki.bench.reporting.verdict import evaluate_candidate_policy


def _load_quality_symbols() -> tuple[Any, Any]:
    quality = import_module("snowiki.bench.runtime.quality")
    contract = import_module("snowiki.bench.contract")
    return quality, contract


def test_quality_metrics_compute_expected_scores(repo_root: Path) -> None:
    quality, _ = _load_quality_symbols()
    recall_at_k = quality.recall_at_k
    reciprocal_rank = quality.reciprocal_rank
    ndcg_at_k = quality.ndcg_at_k

    relevant_ids = {"a", "b"}
    ranked_ids = ["x", "a", "b"]

    assert recall_at_k(relevant_ids, ranked_ids, 2) == 0.5
    assert reciprocal_rank(relevant_ids, ranked_ids) == 0.5
    assert round(ndcg_at_k(relevant_ids, ranked_ids, 3), 6) == 0.693426


def test_evaluate_quality_aggregates_query_results(repo_root: Path) -> None:
    quality, _ = _load_quality_symbols()
    evaluate_quality = quality.evaluate_quality

    ranked_results = {
        "q1": ["a", "x", "b"],
        "q2": ["z", "y", "x"],
    }
    judgments = {
        "q1": ["a", "b"],
        "q2": ["y"],
    }

    summary = evaluate_quality(ranked_results, judgments, top_k=3)

    assert summary.queries_evaluated == 2
    assert summary.top_k == 3
    assert summary.recall_at_k == 1.0
    assert summary.mrr == 0.75
    assert round(summary.ndcg_at_k, 6) == 0.775325
    assert [item.query_id for item in summary.per_query] == ["q1", "q2"]


def test_evaluate_quality_scores_no_answer_abstention_as_perfect() -> None:
    quality, _ = _load_quality_symbols()

    summary = quality.evaluate_quality(
        {"q1": []},
        {"q1": []},
        top_k=3,
        query_no_answer={"q1": True},
    )

    assert summary.queries_evaluated == 1
    assert summary.recall_at_k == 1.0
    assert summary.mrr == 1.0
    assert summary.ndcg_at_k == 1.0
    assert summary.per_query[0].no_answer is True
    assert summary.per_query[0].ranked_ids == ()


def test_evaluate_quality_scores_no_answer_false_positive_as_zero() -> None:
    quality, _ = _load_quality_symbols()

    summary = quality.evaluate_quality(
        {"q1": ["false-positive"]},
        {"q1": []},
        top_k=3,
        query_no_answer={"q1": True},
    )

    assert summary.queries_evaluated == 1
    assert summary.recall_at_k == 0.0
    assert summary.mrr == 0.0
    assert summary.ndcg_at_k == 0.0
    assert summary.per_query[0].ranked_ids == ("false-positive",)


def test_evaluate_quality_aggregates_regular_and_no_answer_queries() -> None:
    quality, _ = _load_quality_symbols()

    summary = quality.evaluate_quality(
        {"q1": ["x", "a", "b"], "q2": []},
        {"q1": ["a", "b"], "q2": []},
        top_k=3,
        query_no_answer={"q2": True},
    )

    assert summary.queries_evaluated == 2
    assert summary.recall_at_k == 1.0
    assert summary.mrr == 0.75
    assert round(summary.ndcg_at_k, 6) == 0.846713
    assert summary.per_query[0].relevant_ids == ("a", "b")


def test_evaluate_quality_can_ignore_no_answer_queries_via_policy() -> None:
    quality, contract = _load_quality_symbols()

    summary = quality.evaluate_quality(
        {"q1": ["a"], "q2": []},
        {"q1": ["a"], "q2": []},
        top_k=3,
        query_no_answer={"q2": True},
        no_answer_policy=contract.NoAnswerScoringPolicy(mode="ignore"),
    )

    assert summary.queries_evaluated == 1
    assert summary.recall_at_k == 1.0
    assert summary.mrr == 1.0
    assert summary.ndcg_at_k == 1.0
    assert [item.query_id for item in summary.per_query] == ["q1"]


def test_evaluate_quality_require_abstention_stays_binary() -> None:
    quality, contract = _load_quality_symbols()

    abstaining = quality.evaluate_quality(
        {"q1": []},
        {"q1": []},
        top_k=3,
        query_no_answer={"q1": True},
        no_answer_policy=contract.NoAnswerScoringPolicy(
            mode="require_abstention",
            false_positive_penalty=0.25,
            abstention_bonus=-0.5,
        ),
    )
    false_positive = quality.evaluate_quality(
        {"q1": ["fp"]},
        {"q1": []},
        top_k=3,
        query_no_answer={"q1": True},
        no_answer_policy=contract.NoAnswerScoringPolicy(
            mode="require_abstention",
            false_positive_penalty=0.25,
            abstention_bonus=-0.5,
        ),
    )

    assert abstaining.recall_at_k == 1.0
    assert abstaining.mrr == 1.0
    assert abstaining.ndcg_at_k == 1.0
    assert false_positive.recall_at_k == 0.0
    assert false_positive.mrr == 0.0
    assert false_positive.ndcg_at_k == 0.0


def test_evaluate_sliced_quality_passes_non_default_no_answer_policy() -> None:
    quality, contract = _load_quality_symbols()

    summary = quality.evaluate_sliced_quality(
        {"q1": ["a"], "q2": ["fp"]},
        {"q1": ["a"], "q2": []},
        query_groups={"q1": "ko", "q2": "mixed"},
        query_kinds={"q1": "known-item", "q2": "topical"},
        top_k=3,
        query_no_answer={"q2": True},
        no_answer_policy=contract.NoAnswerScoringPolicy(
            mode="penalize_false_positives",
            false_positive_penalty=0.25,
        ),
    )

    assert summary.overall.queries_evaluated == 2
    assert summary.overall.recall_at_k == 0.875
    assert summary.by_subset is not None
    assert summary.by_subset["no-answer"].recall_at_k == 0.75


def test_evaluate_sliced_quality_emits_overall_and_slice_metrics(
    repo_root: Path,
) -> None:
    quality, _ = _load_quality_symbols()
    evaluate_sliced_quality = quality.evaluate_sliced_quality

    ranked_results = {
        "ko-001": ["a", "x", "b"],
        "en-001": ["d", "c", "y"],
        "mix-001": ["z", "e", "q"],
    }
    judgments = {
        "ko-001": ["a", "b"],
        "en-001": ["c"],
        "mix-001": ["e"],
    }

    summary = evaluate_sliced_quality(
        ranked_results,
        judgments,
        query_groups={"ko-001": "ko", "en-001": "en", "mix-001": "mixed"},
        query_kinds={
            "ko-001": "known-item",
            "en-001": "topical",
            "mix-001": "temporal",
        },
        top_k=3,
    )

    assert summary.overall.queries_evaluated == 3
    assert summary.by_group["ko"].queries_evaluated == 1
    assert summary.by_group["en"].mrr == 0.5
    assert summary.by_group["mixed"].ndcg_at_k == 0.63093
    assert summary.by_kind["known-item"].recall_at_k == 1.0
    assert summary.by_kind["topical"].mrr == 0.5
    assert summary.by_kind["temporal"].ndcg_at_k == 0.63093


def test_evaluate_quality_thresholds_marks_regressions_as_failures(
    repo_root: Path,
) -> None:
    quality, contract = _load_quality_symbols()
    evaluate_sliced_quality = quality.evaluate_sliced_quality
    evaluate_quality_thresholds = quality.evaluate_quality_thresholds
    benchmark_thresholds = contract.PHASE_1_THRESHOLDS

    summary = evaluate_sliced_quality(
        {"q1": ["miss"], "q2": ["x", "z", "w"]},
        {"q1": ["gold"], "q2": ["y"]},
        query_groups={"q1": "ko", "q2": "en"},
        query_kinds={"q1": "known-item", "q2": "topical"},
        top_k=3,
    )

    report = evaluate_quality_thresholds(
        summary,
        overall_thresholds=benchmark_thresholds["overall"],
        slice_thresholds=benchmark_thresholds["slices"],
    )

    verdicts = {(entry.gate, entry.metric): entry for entry in report}
    assert verdicts[("overall", "recall_at_k")].verdict == "FAIL"
    assert verdicts[("overall", "recall_at_k")].threshold == 0.72
    assert verdicts[("overall", "mrr")].verdict == "FAIL"
    assert verdicts[("overall", "mrr")].threshold == 0.7
    assert verdicts[("overall", "ndcg_at_k")].threshold == 0.67
    assert verdicts[("kind:known-item", "recall_at_k")].verdict == "FAIL"
    assert verdicts[("kind:known-item", "recall_at_k")].threshold == 0.7
    assert verdicts[("kind:known-item", "mrr")].threshold == 0.6
    assert verdicts[("kind:topical", "recall_at_k")].threshold == 0.49
    assert verdicts[("kind:topical", "ndcg_at_k")].verdict == "FAIL"
    assert verdicts[("kind:topical", "ndcg_at_k")].threshold == 0.5
    assert verdicts[("kind:temporal", "recall_at_k")].verdict == "WARN"
    assert verdicts[("kind:temporal", "recall_at_k")].threshold == 0.47
    assert verdicts[("kind:temporal", "recall_at_k")].value == "n/a"


def test_candidate_policy_marks_benchmark_only_when_operational_evidence_is_missing() -> (
    None
):
    control = BaselineResult.model_validate(
        {
            "name": "lexical",
            "latency": {
                "p50_ms": 1.0,
                "p95_ms": 10.0,
                "mean_ms": 1.5,
                "min_ms": 1.0,
                "max_ms": 10.0,
            },
            "quality": {
                "overall": {
                    "recall_at_k": 0.72,
                    "mrr": 0.7,
                    "ndcg_at_k": 0.67,
                    "top_k": 5,
                    "queries_evaluated": 3,
                    "per_query": [],
                },
                "slices": {
                    "group": {
                        "ko": {
                            "recall_at_k": 0.60,
                            "mrr": 0.60,
                            "ndcg_at_k": 0.60,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                        "en": {
                            "recall_at_k": 0.60,
                            "mrr": 0.60,
                            "ndcg_at_k": 0.60,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                        "mixed": {
                            "recall_at_k": 0.60,
                            "mrr": 0.60,
                            "ndcg_at_k": 0.60,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                    },
                    "kind": {},
                },
                "thresholds": [
                    {
                        "gate": "overall",
                        "metric": "recall_at_k",
                        "value": 0.72,
                        "delta": 0.0,
                        "verdict": "PASS",
                        "threshold": 0.72,
                        "warnings": [],
                    },
                    {
                        "gate": "overall",
                        "metric": "mrr",
                        "value": 0.7,
                        "delta": 0.0,
                        "verdict": "PASS",
                        "threshold": 0.7,
                        "warnings": [],
                    },
                    {
                        "gate": "overall",
                        "metric": "ndcg_at_k",
                        "value": 0.67,
                        "delta": 0.0,
                        "verdict": "PASS",
                        "threshold": 0.67,
                        "warnings": [],
                    },
                ],
            },
            "queries": [],
        }
    )
    candidate = BaselineResult.model_validate(
        {
            "name": "bm25s_kiwi_full",
            "tokenizer_name": "kiwi_morphology_v1",
            "latency": {
                "p50_ms": 1.0,
                "p95_ms": 11.0,
                "mean_ms": 1.5,
                "min_ms": 1.0,
                "max_ms": 11.0,
            },
            "quality": {
                "overall": {
                    "recall_at_k": 0.76,
                    "mrr": 0.74,
                    "ndcg_at_k": 0.71,
                    "top_k": 5,
                    "queries_evaluated": 3,
                    "per_query": [],
                },
                "slices": {
                    "group": {
                        "ko": {
                            "recall_at_k": 0.60,
                            "mrr": 0.60,
                            "ndcg_at_k": 0.60,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                        "en": {
                            "recall_at_k": 0.60,
                            "mrr": 0.60,
                            "ndcg_at_k": 0.60,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                        "mixed": {
                            "recall_at_k": 0.64,
                            "mrr": 0.64,
                            "ndcg_at_k": 0.64,
                            "top_k": 5,
                            "queries_evaluated": 1,
                            "per_query": [],
                        },
                    },
                    "kind": {},
                },
                "thresholds": [
                    {
                        "gate": "overall",
                        "metric": "recall_at_k",
                        "value": 0.76,
                        "delta": 0.04,
                        "verdict": "PASS",
                        "threshold": 0.72,
                        "warnings": [],
                    },
                    {
                        "gate": "overall",
                        "metric": "mrr",
                        "value": 0.74,
                        "delta": 0.04,
                        "verdict": "PASS",
                        "threshold": 0.7,
                        "warnings": [],
                    },
                    {
                        "gate": "overall",
                        "metric": "ndcg_at_k",
                        "value": 0.71,
                        "delta": 0.04,
                        "verdict": "PASS",
                        "threshold": 0.67,
                        "warnings": [],
                    },
                ],
            },
            "queries": [],
        }
    )
    matrix = CandidateMatrixReport(
        candidates=[
            CandidateMatrixEntry(
                candidate_name="regex_v1",
                evidence_baseline="lexical",
                role="control",
                admission_status="admitted",
                control=True,
                operational_evidence=CandidateOperationalEvidence(
                    memory_peak_rss_mb=None,
                    memory_evidence_status="not_measured",
                    disk_size_mb=None,
                    disk_size_evidence_status="not_measured",
                    platform_support=PlatformSupportEvidence(
                        macos="supported",
                        linux_x86_64="supported",
                        linux_aarch64="supported",
                        windows="supported",
                        fallback_behavior="none",
                    ),
                    install_ergonomics=InstallErgonomicsEvidence(
                        prebuilt_available=True,
                        build_from_source_required=False,
                        hidden_bootstrap_steps=False,
                        operational_complexity="low",
                    ),
                    zero_cost_admission=True,
                    admission_reason="current_runtime_default",
                ),
                baseline=control,
            ),
            CandidateMatrixEntry(
                candidate_name="kiwi_morphology_v1",
                evidence_baseline="bm25s_kiwi_full",
                role="candidate",
                admission_status="admitted",
                control=False,
                baseline=candidate,
            ),
        ]
    )

    decisions = {
        entry.candidate_name: entry for entry in evaluate_candidate_policy(matrix)
    }

    assert decisions["regex_v1"].disposition == "benchmark_only"
    assert decisions["regex_v1"].operational_evidence_present is False
    assert decisions["regex_v1"].reasons == ["missing_operational_evidence"]
    assert decisions["kiwi_morphology_v1"].disposition == "benchmark_only"
    assert decisions["kiwi_morphology_v1"].operational_evidence_present is False
    assert decisions["kiwi_morphology_v1"].mixed_deltas == {
        "recall_at_k": 0.04,
        "mrr": 0.04,
        "ndcg_at_k": 0.04,
    }
    assert decisions["kiwi_morphology_v1"].latency_p95_ratio == 1.1
    assert "missing_operational_evidence" in decisions["kiwi_morphology_v1"].reasons


def test_evaluate_quality_counts_no_answer_queries_and_exposes_multi_k() -> None:
    quality, _ = _load_quality_symbols()
    summary = quality.evaluate_quality(
        {"q1": ["a"], "q2": ["x", "y"]},
        {"q1": ["a"], "q2": []},
        top_k=5,
        top_ks=(1, 3, 5),
        query_no_answer={"q2": True},
        query_tags={"q1": ("known-answer",), "q2": ("no-answer",)},
    )

    assert summary.queries_evaluated == 2
    assert summary.recall_at_k == 0.5
    assert summary.mrr == 0.5
    assert summary.ndcg_at_k == 0.5
    assert summary.top_ks == (1, 3, 5)
    assert summary.metrics_by_k is not None
    assert set(summary.metrics_by_k) == {"recall_at_k", "mrr", "ndcg_at_k"}
    assert summary.metrics_by_k["recall_at_k"] == {1: 0.5, 3: 0.5, 5: 0.5}
    assert summary.metrics_by_k["mrr"] == {1: 0.5, 3: 0.5, 5: 0.5}
    assert summary.metrics_by_k["ndcg_at_k"] == {1: 0.5, 3: 0.5, 5: 0.5}
    assert summary.per_query[1].no_answer is True
    assert summary.per_query[1].tags == ("no-answer",)


def test_evaluate_sliced_quality_emits_subset_slices_from_tags_and_no_answer() -> None:
    quality, _ = _load_quality_symbols()
    summary = quality.evaluate_sliced_quality(
        {"q1": ["a"], "q2": ["x"], "q3": ["c"]},
        {"q1": ["a"], "q2": [], "q3": ["c"]},
        query_groups={"q1": "ko", "q2": "mixed", "q3": "en"},
        query_kinds={"q1": "known-item", "q2": "topical", "q3": "temporal"},
        query_tags={"q1": ("identifier",), "q2": ("ambiguous",), "q3": ("path",)},
        query_no_answer={"q2": True},
        top_k=5,
        top_ks=(1, 5),
    )

    assert summary.by_subset is not None
    assert set(summary.by_subset) >= {"identifier", "ambiguous", "path", "no-answer", "has-answer"}
    assert summary.by_subset["no-answer"].queries_evaluated == 1
