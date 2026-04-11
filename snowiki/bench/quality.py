from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .contract import MetricThreshold, ReportEntry


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


@dataclass(frozen=True)
class SlicedQualitySummary:
    overall: QualitySummary
    by_group: dict[str, QualitySummary]
    by_kind: dict[str, QualitySummary]
    threshold_report: tuple[ReportEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.to_dict(),
            "slices": {
                "group": {
                    name: summary.to_dict() for name, summary in self.by_group.items()
                },
                "kind": {
                    name: summary.to_dict() for name, summary in self.by_kind.items()
                },
            },
            "thresholds": [asdict(entry) for entry in self.threshold_report],
        }


def _evaluate_slice(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    query_ids: list[str],
    *,
    top_k: int,
) -> QualitySummary:
    filtered_ranked_results = {
        query_id: ranked_results.get(query_id, []) for query_id in query_ids
    }
    filtered_judgments = {
        query_id: judgments[query_id] for query_id in query_ids if query_id in judgments
    }
    return evaluate_quality(filtered_ranked_results, filtered_judgments, top_k=top_k)


def _ordered_labels(
    labels_by_query: dict[str, str],
    query_ids: list[str],
    preferred: tuple[str, ...],
) -> tuple[str, ...]:
    seen = {
        labels_by_query[query_id]
        for query_id in query_ids
        if query_id in labels_by_query
    }
    ordered = list(preferred)
    ordered.extend(sorted(seen.difference(preferred)))
    return tuple(ordered)


def evaluate_sliced_quality(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    *,
    query_groups: dict[str, str],
    query_kinds: dict[str, str],
    top_k: int,
    group_labels: tuple[str, ...] = ("ko", "en", "mixed"),
    kind_labels: tuple[str, ...] = ("known-item", "topical", "temporal"),
) -> SlicedQualitySummary:
    query_ids = [
        query_id
        for query_id in judgments
        if query_id in ranked_results or query_id in query_groups
    ]
    overall = _evaluate_slice(ranked_results, judgments, query_ids, top_k=top_k)

    ordered_groups = _ordered_labels(query_groups, query_ids, group_labels)
    ordered_kinds = _ordered_labels(query_kinds, query_ids, kind_labels)

    by_group = {
        group: _evaluate_slice(
            ranked_results,
            judgments,
            [query_id for query_id in query_ids if query_groups.get(query_id) == group],
            top_k=top_k,
        )
        for group in ordered_groups
    }
    by_kind = {
        kind: _evaluate_slice(
            ranked_results,
            judgments,
            [query_id for query_id in query_ids if query_kinds.get(query_id) == kind],
            top_k=top_k,
        )
        for kind in ordered_kinds
    }

    return SlicedQualitySummary(overall=overall, by_group=by_group, by_kind=by_kind)


def _metric_value(summary: QualitySummary, metric: str) -> float:
    return float(getattr(summary, metric))


def _evaluate_threshold(
    *,
    gate: str,
    summary: QualitySummary,
    threshold: MetricThreshold,
) -> ReportEntry:
    if summary.queries_evaluated == 0:
        return ReportEntry(
            gate=gate,
            metric=threshold.metric,
            value="n/a",
            delta=None,
            verdict="WARN",
            threshold=threshold.value,
            warnings=[f"gate '{gate}' was not evaluated"],
        )

    metric_value = round(_metric_value(summary, threshold.metric), 6)
    if threshold.operator == ">=":
        delta = round(metric_value - threshold.value, 6)
        verdict = "PASS" if metric_value >= threshold.value else "FAIL"
    else:
        delta = round(threshold.value - metric_value, 6)
        verdict = "PASS" if metric_value <= threshold.value else "FAIL"

    return ReportEntry(
        gate=gate,
        metric=threshold.metric,
        value=metric_value,
        delta=delta,
        verdict=verdict,
        threshold=threshold.value,
        warnings=[],
    )


def evaluate_quality_thresholds(
    summary: SlicedQualitySummary,
    *,
    overall_thresholds: list[MetricThreshold],
    slice_thresholds: dict[str, list[MetricThreshold]],
) -> tuple[ReportEntry, ...]:
    report: list[ReportEntry] = []
    allowed_metrics = {"recall_at_k", "mrr", "ndcg_at_k"}

    for threshold in overall_thresholds:
        if threshold.metric not in allowed_metrics:
            continue
        report.append(
            _evaluate_threshold(
                gate="overall", summary=summary.overall, threshold=threshold
            )
        )

    for kind, thresholds in slice_thresholds.items():
        kind_summary = summary.by_kind.get(kind)
        if kind_summary is None:
            continue
        for threshold in thresholds:
            if threshold.metric not in allowed_metrics:
                continue
            report.append(
                _evaluate_threshold(
                    gate=f"kind:{kind}",
                    summary=kind_summary,
                    threshold=threshold,
                )
            )

    return tuple(report)


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
