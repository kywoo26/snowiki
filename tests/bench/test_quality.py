from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


def _load_quality_symbols() -> tuple[Any, Any]:
    quality = import_module("snowiki.bench.quality")
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
    phase_1_thresholds = contract.PHASE_1_THRESHOLDS

    summary = evaluate_sliced_quality(
        {"q1": ["miss"], "q2": ["x", "z", "w"]},
        {"q1": ["gold"], "q2": ["y"]},
        query_groups={"q1": "ko", "q2": "en"},
        query_kinds={"q1": "known-item", "q2": "topical"},
        top_k=3,
    )

    report = evaluate_quality_thresholds(
        summary,
        overall_thresholds=phase_1_thresholds["overall"],
        slice_thresholds=phase_1_thresholds["slices"],
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
