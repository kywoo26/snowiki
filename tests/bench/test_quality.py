from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_QUALITY = import_module("snowiki.bench.quality")
_CONTRACT = import_module("snowiki.bench.contract")
evaluate_quality = _QUALITY.evaluate_quality
evaluate_quality_thresholds = _QUALITY.evaluate_quality_thresholds
evaluate_sliced_quality = _QUALITY.evaluate_sliced_quality
ndcg_at_k = _QUALITY.ndcg_at_k
PHASE_1_THRESHOLDS = _CONTRACT.PHASE_1_THRESHOLDS
recall_at_k = _QUALITY.recall_at_k
reciprocal_rank = _QUALITY.reciprocal_rank


def test_quality_metrics_compute_expected_scores() -> None:
    relevant_ids = {"a", "b"}
    ranked_ids = ["x", "a", "b"]

    assert recall_at_k(relevant_ids, ranked_ids, 2) == 0.5
    assert reciprocal_rank(relevant_ids, ranked_ids) == 0.5
    assert round(ndcg_at_k(relevant_ids, ranked_ids, 3), 6) == 0.693426


def test_evaluate_quality_aggregates_query_results() -> None:
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


def test_evaluate_sliced_quality_emits_overall_and_slice_metrics() -> None:
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


def test_evaluate_quality_thresholds_marks_regressions_as_failures() -> None:
    summary = evaluate_sliced_quality(
        {"q1": ["miss"], "q2": ["x", "z", "w"]},
        {"q1": ["gold"], "q2": ["y"]},
        query_groups={"q1": "ko", "q2": "en"},
        query_kinds={"q1": "known-item", "q2": "topical"},
        top_k=3,
    )

    report = evaluate_quality_thresholds(
        summary,
        overall_thresholds=PHASE_1_THRESHOLDS["overall"],
        slice_thresholds=PHASE_1_THRESHOLDS["slices"],
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
