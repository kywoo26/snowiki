from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


def recall_at_k(relevant_ids: set[str], ranked_ids: list[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    hits = len(relevant_ids.intersection(ranked_ids[:k]))
    return hits / len(relevant_ids)


def reciprocal_rank(relevant_ids: set[str], ranked_ids: list[str]) -> float:
    for index, item in enumerate(ranked_ids, start=1):
        if item in relevant_ids:
            return 1.0 / index
    return 0.0


def ndcg_at_k(relevant_ids: set[str], ranked_ids: list[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    discounted_gain = 0.0
    for index, item in enumerate(ranked_ids[:k], start=1):
        if item in relevant_ids:
            discounted_gain += 1.0 / math.log2(index + 1)
    ideal_hits = min(len(relevant_ids), k)
    if ideal_hits == 0:
        return 0.0
    ideal_discounted_gain = sum(
        1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1)
    )
    if ideal_discounted_gain == 0.0:
        return 0.0
    return discounted_gain / ideal_discounted_gain


@dataclass(frozen=True)
class QueryQualityResult:
    query_id: str
    ranked_ids: tuple[str, ...]
    relevant_ids: tuple[str, ...]
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualitySummary:
    queries_evaluated: int
    top_k: int
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    per_query: tuple[QueryQualityResult, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["per_query"] = [item.to_dict() for item in self.per_query]
        return payload


def evaluate_quality(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    *,
    top_k: int,
) -> QualitySummary:
    per_query: list[QueryQualityResult] = []
    recall_total = 0.0
    reciprocal_rank_total = 0.0
    ndcg_total = 0.0
    evaluated = 0

    for query_id, relevant in judgments.items():
        relevant_ids = {str(item) for item in relevant}
        if not relevant_ids:
            continue
        ranked_ids = [str(item) for item in ranked_results.get(query_id, [])]
        recall_score = recall_at_k(relevant_ids, ranked_ids, top_k)
        reciprocal_score = reciprocal_rank(relevant_ids, ranked_ids)
        ndcg_score = ndcg_at_k(relevant_ids, ranked_ids, top_k)
        per_query.append(
            QueryQualityResult(
                query_id=query_id,
                ranked_ids=tuple(ranked_ids[:top_k]),
                relevant_ids=tuple(sorted(relevant_ids)),
                recall_at_k=round(recall_score, 6),
                reciprocal_rank=round(reciprocal_score, 6),
                ndcg_at_k=round(ndcg_score, 6),
            )
        )
        recall_total += recall_score
        reciprocal_rank_total += reciprocal_score
        ndcg_total += ndcg_score
        evaluated += 1

    if evaluated == 0:
        return QualitySummary(
            queries_evaluated=0,
            top_k=top_k,
            recall_at_k=0.0,
            mrr=0.0,
            ndcg_at_k=0.0,
            per_query=(),
        )

    return QualitySummary(
        queries_evaluated=evaluated,
        top_k=top_k,
        recall_at_k=round(recall_total / evaluated, 6),
        mrr=round(reciprocal_rank_total / evaluated, 6),
        ndcg_at_k=round(ndcg_total / evaluated, 6),
        per_query=tuple(per_query),
    )
