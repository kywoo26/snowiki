from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

_TOKEN_RE = re.compile(r"[가-힣]+|[a-z0-9]+", re.IGNORECASE)


def count_tokens(text: str) -> int:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return len(_TOKEN_RE.findall(normalized))


def summarize_token_usage(contexts: list[str]) -> dict[str, float]:
    token_counts = [count_tokens(item) for item in contexts]
    if not token_counts:
        return {"avg_tokens": 0.0, "min_tokens": 0.0, "max_tokens": 0.0}
    return {
        "avg_tokens": round(sum(token_counts) / len(token_counts), 6),
        "min_tokens": float(min(token_counts)),
        "max_tokens": float(max(token_counts)),
    }


@dataclass(frozen=True)
class TokenReductionSummary:
    baseline: str
    reference_baseline: str
    avg_tokens: float
    reference_avg_tokens: float
    tokens_saved: float
    reduction_ratio: float
    paired_quality: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_token_usage(
    token_usage_by_baseline: dict[str, dict[str, float]],
    quality_by_baseline: dict[str, dict[str, float]],
    *,
    reference_baseline: str = "raw",
) -> dict[str, TokenReductionSummary]:
    reference = token_usage_by_baseline.get(reference_baseline, {"avg_tokens": 0.0})
    reference_avg_tokens = float(reference.get("avg_tokens", 0.0))
    results: dict[str, TokenReductionSummary] = {}
    for baseline, usage in token_usage_by_baseline.items():
        avg_tokens = float(usage.get("avg_tokens", 0.0))
        tokens_saved = reference_avg_tokens - avg_tokens
        reduction_ratio = (
            (tokens_saved / reference_avg_tokens) if reference_avg_tokens else 0.0
        )
        results[baseline] = TokenReductionSummary(
            baseline=baseline,
            reference_baseline=reference_baseline,
            avg_tokens=round(avg_tokens, 6),
            reference_avg_tokens=round(reference_avg_tokens, 6),
            tokens_saved=round(tokens_saved, 6),
            reduction_ratio=round(reduction_ratio, 6),
            paired_quality={
                "recall_at_k": round(
                    float(
                        quality_by_baseline.get(baseline, {}).get("recall_at_k", 0.0)
                    ),
                    6,
                ),
                "mrr": round(
                    float(quality_by_baseline.get(baseline, {}).get("mrr", 0.0)), 6
                ),
                "ndcg_at_k": round(
                    float(quality_by_baseline.get(baseline, {}).get("ndcg_at_k", 0.0)),
                    6,
                ),
            },
        )
    return results
