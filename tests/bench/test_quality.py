from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_QUALITY = import_module("snowiki.bench.quality")
evaluate_quality = _QUALITY.evaluate_quality
ndcg_at_k = _QUALITY.ndcg_at_k
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
