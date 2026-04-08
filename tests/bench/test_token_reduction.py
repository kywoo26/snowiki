from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TOKEN_REDUCTION = import_module("snowiki.bench.token_reduction")
compare_token_usage = _TOKEN_REDUCTION.compare_token_usage
count_tokens = _TOKEN_REDUCTION.count_tokens
summarize_token_usage = _TOKEN_REDUCTION.summarize_token_usage


def test_count_tokens_handles_mixed_language_text() -> None:
    assert count_tokens("Snowiki 개인 wiki benchmark") == 4


def test_summarize_token_usage_returns_aggregate_ranges() -> None:
    summary = summarize_token_usage(["one two three", "one two"])

    assert summary["avg_tokens"] == 2.5
    assert summary["min_tokens"] == 2.0
    assert summary["max_tokens"] == 3.0


def test_compare_token_usage_pairs_reduction_with_quality() -> None:
    token_usage = {
        "raw": {"avg_tokens": 100.0},
        "current": {"avg_tokens": 60.0},
        "v2": {"avg_tokens": 40.0},
    }
    quality = {
        "raw": {"recall_at_k": 0.8, "mrr": 0.7, "ndcg_at_k": 0.75},
        "current": {"recall_at_k": 0.8, "mrr": 0.72, "ndcg_at_k": 0.78},
        "v2": {"recall_at_k": 0.82, "mrr": 0.76, "ndcg_at_k": 0.8},
    }

    summary = compare_token_usage(token_usage, quality)

    assert summary["raw"].reduction_ratio == 0.0
    assert summary["current"].tokens_saved == 40.0
    assert summary["current"].reduction_ratio == 0.4
    assert summary["v2"].paired_quality["ndcg_at_k"] == 0.8
