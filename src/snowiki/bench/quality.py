"""Quality metrics and threshold evaluation for benchmark runs."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from .contract import MetricThreshold, ReportEntry


def recall_at_k(relevant_ids: set[str], ranked_ids: list[str], k: int) -> float:
    if not relevant_ids or k <= 0:
        return 0.0
    hits = len(relevant_ids.intersection(ranked_ids[:k]))
    return hits / len(relevant_ids)


def reciprocal_rank(relevant_ids: set[str], ranked_ids: list[str], *, k: int | None = None) -> float:
    limited = ranked_ids if k is None else ranked_ids[:k]
    for index, item in enumerate(limited, start=1):
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
    ideal_discounted_gain = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    if ideal_discounted_gain == 0.0:
        return 0.0
    return discounted_gain / ideal_discounted_gain


@dataclass(frozen=True)
class QueryQualityResult:
    query_id: str
    ranked_ids: tuple[str, ...]
    relevant_ids: tuple[str, ...]
    tags: tuple[str, ...] = ()
    no_answer: bool = False
    recall_at_k: float = 0.0
    reciprocal_rank: float = 0.0
    ndcg_at_k: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QualitySummary:
    queries_evaluated: int
    top_k: int
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    top_ks: tuple[int, ...] = ()
    metrics_by_k: dict[str, dict[int, float]] | None = None
    per_query: tuple[QueryQualityResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['per_query'] = [item.to_dict() for item in self.per_query]
        if self.metrics_by_k is None:
            payload['metrics_by_k'] = {}
        else:
            payload['metrics_by_k'] = {
                metric: {str(k): value for k, value in values.items()}
                for metric, values in self.metrics_by_k.items()
            }
        return payload


@dataclass(frozen=True)
class SlicedQualitySummary:
    overall: QualitySummary
    by_group: dict[str, QualitySummary]
    by_kind: dict[str, QualitySummary]
    by_subset: dict[str, QualitySummary] | None = None
    threshold_report: tuple[ReportEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            'overall': self.overall.to_dict(),
            'slices': {
                'group': {name: summary.to_dict() for name, summary in self.by_group.items()},
                'kind': {name: summary.to_dict() for name, summary in self.by_kind.items()},
                'subset': {name: summary.to_dict() for name, summary in (self.by_subset or {}).items()},
            },
            'thresholds': [asdict(entry) for entry in self.threshold_report],
        }


def _ordered_labels(labels_by_query: dict[str, str], query_ids: list[str], preferred: tuple[str, ...]) -> tuple[str, ...]:
    seen = {labels_by_query[query_id] for query_id in query_ids if query_id in labels_by_query}
    ordered = list(preferred)
    ordered.extend(sorted(seen.difference(preferred)))
    return tuple(ordered)


def _normalize_top_ks(top_k: int, top_ks: tuple[int, ...] | list[int] | None) -> tuple[int, ...]:
    values = {int(top_k)}
    for value in top_ks or ():
        ivalue = int(value)
        if ivalue > 0:
            values.add(ivalue)
    return tuple(sorted(values))


def evaluate_quality(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    *,
    top_k: int,
    top_ks: tuple[int, ...] | list[int] | None = None,
    query_tags: dict[str, tuple[str, ...]] | None = None,
    query_no_answer: dict[str, bool] | None = None,
) -> QualitySummary:
    per_query: list[QueryQualityResult] = []
    ks = _normalize_top_ks(top_k, top_ks)
    recall_totals = defaultdict(float)
    mrr_totals = defaultdict(float)
    ndcg_totals = defaultdict(float)
    evaluated = 0
    query_tags = query_tags or {}
    query_no_answer = query_no_answer or {}

    for query_id, relevant in judgments.items():
        relevant_ids = {str(item) for item in relevant}
        no_answer = bool(query_no_answer.get(query_id, False))
        if not relevant_ids and not no_answer:
            continue
        ranked_ids = [str(item) for item in ranked_results.get(query_id, [])]
        metrics_per_k = {}
        for k in ks:
            metrics_per_k[k] = {
                'recall_at_k': recall_at_k(relevant_ids, ranked_ids, k),
                'mrr': reciprocal_rank(relevant_ids, ranked_ids, k=k),
                'ndcg_at_k': ndcg_at_k(relevant_ids, ranked_ids, k),
            }
            recall_totals[k] += metrics_per_k[k]['recall_at_k']
            mrr_totals[k] += metrics_per_k[k]['mrr']
            ndcg_totals[k] += metrics_per_k[k]['ndcg_at_k']
        chosen = metrics_per_k[top_k]
        per_query.append(
            QueryQualityResult(
                query_id=query_id,
                ranked_ids=tuple(ranked_ids[:top_k]),
                relevant_ids=tuple(sorted(relevant_ids)),
                tags=tuple(query_tags.get(query_id, ())),
                no_answer=no_answer,
                recall_at_k=round(chosen['recall_at_k'], 6),
                reciprocal_rank=round(chosen['mrr'], 6),
                ndcg_at_k=round(chosen['ndcg_at_k'], 6),
            )
        )
        evaluated += 1

    if evaluated == 0:
        return QualitySummary(
            queries_evaluated=0,
            top_k=top_k,
            recall_at_k=0.0,
            mrr=0.0,
            ndcg_at_k=0.0,
            top_ks=ks,
            metrics_by_k={
                'recall_at_k': dict.fromkeys(ks, 0.0),
                'mrr': dict.fromkeys(ks, 0.0),
                'ndcg_at_k': dict.fromkeys(ks, 0.0),
            },
            per_query=(),
        )

    metrics_by_k = {
        'recall_at_k': {k: round(recall_totals[k] / evaluated, 6) for k in ks},
        'mrr': {k: round(mrr_totals[k] / evaluated, 6) for k in ks},
        'ndcg_at_k': {k: round(ndcg_totals[k] / evaluated, 6) for k in ks},
    }
    return QualitySummary(
        queries_evaluated=evaluated,
        top_k=top_k,
        recall_at_k=metrics_by_k['recall_at_k'][top_k],
        mrr=metrics_by_k['mrr'][top_k],
        ndcg_at_k=metrics_by_k['ndcg_at_k'][top_k],
        top_ks=ks,
        metrics_by_k=metrics_by_k,
        per_query=tuple(per_query),
    )


def _evaluate_slice(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    query_ids: list[str],
    *,
    top_k: int,
    top_ks: tuple[int, ...] | list[int] | None,
    query_tags: dict[str, tuple[str, ...]],
    query_no_answer: dict[str, bool],
) -> QualitySummary:
    filtered_ranked_results = {query_id: ranked_results.get(query_id, []) for query_id in query_ids}
    filtered_judgments = {query_id: judgments.get(query_id, []) for query_id in query_ids}
    return evaluate_quality(
        filtered_ranked_results,
        filtered_judgments,
        top_k=top_k,
        top_ks=top_ks,
        query_tags={query_id: query_tags.get(query_id, ()) for query_id in query_ids},
        query_no_answer={query_id: query_no_answer.get(query_id, False) for query_id in query_ids},
    )


def evaluate_sliced_quality(
    ranked_results: dict[str, list[str]],
    judgments: dict[str, list[str]],
    *,
    query_groups: dict[str, str],
    query_kinds: dict[str, str],
    top_k: int,
    top_ks: tuple[int, ...] | list[int] | None = None,
    query_tags: dict[str, tuple[str, ...]] | None = None,
    query_no_answer: dict[str, bool] | None = None,
    group_labels: tuple[str, ...] = ('ko', 'en', 'mixed'),
    kind_labels: tuple[str, ...] = ('known-item', 'topical', 'temporal'),
) -> SlicedQualitySummary:
    query_ids = [query_id for query_id in query_groups if query_id in ranked_results or query_id in judgments]
    query_tags = query_tags or {}
    query_no_answer = query_no_answer or {}
    overall = _evaluate_slice(ranked_results, judgments, query_ids, top_k=top_k, top_ks=top_ks, query_tags=query_tags, query_no_answer=query_no_answer)
    ordered_groups = _ordered_labels(query_groups, query_ids, group_labels)
    ordered_kinds = _ordered_labels(query_kinds, query_ids, kind_labels)
    by_group = {
        group: _evaluate_slice(
            ranked_results,
            judgments,
            [query_id for query_id in query_ids if query_groups.get(query_id) == group],
            top_k=top_k,
            top_ks=top_ks,
            query_tags=query_tags,
            query_no_answer=query_no_answer,
        )
        for group in ordered_groups
    }
    by_kind = {
        kind: _evaluate_slice(
            ranked_results,
            judgments,
            [query_id for query_id in query_ids if query_kinds.get(query_id) == kind],
            top_k=top_k,
            top_ks=top_ks,
            query_tags=query_tags,
            query_no_answer=query_no_answer,
        )
        for kind in ordered_kinds
    }
    subset_ids: dict[str, list[str]] = defaultdict(list)
    for query_id in query_ids:
        tags = set(query_tags.get(query_id, ()))
        if query_no_answer.get(query_id, False):
            tags.add('no-answer')
        else:
            tags.add('has-answer')
        for tag in tags:
            subset_ids[tag].append(query_id)
    by_subset = {
        name: _evaluate_slice(
            ranked_results,
            judgments,
            ids,
            top_k=top_k,
            top_ks=top_ks,
            query_tags=query_tags,
            query_no_answer=query_no_answer,
        )
        for name, ids in sorted(subset_ids.items())
    }
    return SlicedQualitySummary(overall=overall, by_group=by_group, by_kind=by_kind, by_subset=by_subset)


def _metric_value(summary: QualitySummary, metric: str) -> float:
    return float(getattr(summary, metric))


def _evaluate_threshold(*, gate: str, summary: QualitySummary, threshold: MetricThreshold) -> ReportEntry:
    if summary.queries_evaluated == 0:
        return ReportEntry(gate=gate, metric=threshold.metric, value='n/a', delta=None, verdict='WARN', threshold=threshold.value, warnings=[f"gate '{gate}' was not evaluated"])
    metric_value = round(_metric_value(summary, threshold.metric), 6)
    if threshold.operator == '>=':
        delta = round(metric_value - threshold.value, 6)
        verdict = 'PASS' if metric_value >= threshold.value else 'FAIL'
    else:
        delta = round(threshold.value - metric_value, 6)
        verdict = 'PASS' if metric_value <= threshold.value else 'FAIL'
    return ReportEntry(gate=gate, metric=threshold.metric, value=metric_value, delta=delta, verdict=verdict, threshold=threshold.value, warnings=[])


def evaluate_quality_thresholds(summary: SlicedQualitySummary, *, overall_thresholds: list[MetricThreshold], slice_thresholds: dict[str, list[MetricThreshold]]) -> tuple[ReportEntry, ...]:
    report: list[ReportEntry] = []
    allowed_metrics = {'recall_at_k', 'mrr', 'ndcg_at_k'}
    for threshold in overall_thresholds:
        if threshold.metric not in allowed_metrics:
            continue
        report.append(_evaluate_threshold(gate='overall', summary=summary.overall, threshold=threshold))
    for kind, thresholds in slice_thresholds.items():
        kind_summary = summary.by_kind.get(kind)
        if kind_summary is None:
            continue
        for threshold in thresholds:
            if threshold.metric not in allowed_metrics:
                continue
            report.append(_evaluate_threshold(gate=f'kind:{kind}', summary=kind_summary, threshold=threshold))
    return tuple(report)
