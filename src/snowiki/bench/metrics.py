from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from .normalization import normalize_query_results
from .specs import MetricResult, QueryResult

type MetricComputeFn = Callable[[Sequence[object], Mapping[str, Any]], MetricResult]


class MetricRegistry:
    """Registry for benchmark metric functions."""

    def __init__(self) -> None:
        self._compute_fns: dict[str, MetricComputeFn] = {}

    def register_metric(self, metric_id: str, compute_fn: MetricComputeFn) -> None:
        if metric_id in self._compute_fns:
            raise ValueError(f"Metric already registered: {metric_id}")
        self._compute_fns[metric_id] = compute_fn

    def compute(
        self,
        metric_id: str,
        results: Sequence[object],
        qrels: Mapping[str, Any],
    ) -> MetricResult:
        try:
            compute_fn = self._compute_fns[metric_id]
        except KeyError as exc:
            raise KeyError(f"Unknown benchmark metric: {metric_id}") from exc
        return compute_fn(results, qrels)

    def list_metrics(self) -> tuple[str, ...]:
        return tuple(self._compute_fns)


def recall_at_100(results: Sequence[object], qrels: Mapping[str, Any]) -> MetricResult:
    per_query_scores: dict[str, float] = {}
    normalized_qrels = _normalize_qrels(qrels)
    for result in _normalize_query_results(results):
        relevant_doc_ids = normalized_qrels.get(result.query_id, frozenset())
        if not relevant_doc_ids:
            continue
        retrieved = set(result.ranked_doc_ids[:100])
        per_query_scores[result.query_id] = len(retrieved & relevant_doc_ids) / len(relevant_doc_ids)
    return MetricResult(
        metric_id="recall_at_100",
        value=_mean_or_none(per_query_scores.values()),
        details={
            "evaluated_queries": len(per_query_scores),
            "per_query": per_query_scores,
        },
    )


def mrr_at_10(results: Sequence[object], qrels: Mapping[str, Any]) -> MetricResult:
    per_query_scores: dict[str, float] = {}
    normalized_qrels = _normalize_qrels(qrels)
    for result in _normalize_query_results(results):
        relevant_doc_ids = normalized_qrels.get(result.query_id, frozenset())
        if not relevant_doc_ids:
            continue
        reciprocal_rank = 0.0
        for rank, doc_id in enumerate(result.ranked_doc_ids[:10], start=1):
            if doc_id in relevant_doc_ids:
                reciprocal_rank = 1.0 / rank
                break
        per_query_scores[result.query_id] = reciprocal_rank
    return MetricResult(
        metric_id="mrr_at_10",
        value=_mean_or_none(per_query_scores.values()),
        details={
            "evaluated_queries": len(per_query_scores),
            "per_query": per_query_scores,
        },
    )


def ndcg_at_10(results: Sequence[object], qrels: Mapping[str, Any]) -> MetricResult:
    per_query_scores: dict[str, float] = {}
    normalized_qrels = _normalize_qrels(qrels)
    for result in _normalize_query_results(results):
        relevant_doc_ids = normalized_qrels.get(result.query_id, frozenset())
        if not relevant_doc_ids:
            continue
        dcg = 0.0
        for rank, doc_id in enumerate(result.ranked_doc_ids[:10], start=1):
            if doc_id in relevant_doc_ids:
                dcg += 1.0 / math.log2(rank + 1)
        ideal_hits = min(len(relevant_doc_ids), 10)
        ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        per_query_scores[result.query_id] = dcg / ideal_dcg if ideal_dcg else 0.0
    return MetricResult(
        metric_id="ndcg_at_10",
        value=_mean_or_none(per_query_scores.values()),
        details={
            "evaluated_queries": len(per_query_scores),
            "per_query": per_query_scores,
        },
    )


def latency_p50_ms(results: Sequence[object], qrels: Mapping[str, Any]) -> MetricResult:
    del qrels
    per_query_latencies = _normalize_latency_results(results)
    return MetricResult(
        metric_id="latency_p50_ms",
        value=_percentile(tuple(per_query_latencies.values()), 0.5),
        details={
            "samples": len(per_query_latencies),
            "per_query": per_query_latencies,
        },
    )


def latency_p95_ms(results: Sequence[object], qrels: Mapping[str, Any]) -> MetricResult:
    del qrels
    per_query_latencies = _normalize_latency_results(results)
    return MetricResult(
        metric_id="latency_p95_ms",
        value=_percentile(tuple(per_query_latencies.values()), 0.95),
        details={
            "samples": len(per_query_latencies),
            "per_query": per_query_latencies,
        },
    )


BUILTIN_METRICS: tuple[str, ...] = (
    "recall_at_100",
    "mrr_at_10",
    "ndcg_at_10",
    "latency_p50_ms",
    "latency_p95_ms",
)
DEFAULT_METRIC_REGISTRY = MetricRegistry()

DEFAULT_METRIC_REGISTRY.register_metric("recall_at_100", recall_at_100)
DEFAULT_METRIC_REGISTRY.register_metric("mrr_at_10", mrr_at_10)
DEFAULT_METRIC_REGISTRY.register_metric("ndcg_at_10", ndcg_at_10)
DEFAULT_METRIC_REGISTRY.register_metric("latency_p50_ms", latency_p50_ms)
DEFAULT_METRIC_REGISTRY.register_metric("latency_p95_ms", latency_p95_ms)


def register_metric(metric_id: str, compute_fn: MetricComputeFn) -> None:
    """Register one metric on the default registry."""

    DEFAULT_METRIC_REGISTRY.register_metric(metric_id, compute_fn)


def compute(
    metric_id: str,
    results: Sequence[object],
    qrels: Mapping[str, Any],
) -> MetricResult:
    """Compute one registered metric from the default registry."""

    return DEFAULT_METRIC_REGISTRY.compute(metric_id, results, qrels)


def _normalize_qrels(qrels: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    normalized: dict[str, frozenset[str]] = {}
    for query_id, relevant_doc_ids in qrels.items():
        if not isinstance(query_id, str):
            raise TypeError("Benchmark qrels query IDs must be strings.")
        if not isinstance(relevant_doc_ids, Sequence | set | frozenset) or isinstance(
            relevant_doc_ids,
            str | bytes,
        ):
            raise TypeError("Benchmark qrels must map query IDs to collections of doc IDs.")
        normalized[query_id] = frozenset(str(doc_id) for doc_id in relevant_doc_ids)
    return normalized


def _normalize_query_results(results: Sequence[object]) -> tuple[QueryResult, ...]:
    return normalize_query_results(results)


def _normalize_latency_results(results: Sequence[object]) -> dict[str, float]:
    per_query_latencies: dict[str, float] = {}
    for item in results:
        if isinstance(item, QueryResult):
            if item.latency_ms is None:
                continue
            per_query_latencies[item.query_id] = float(item.latency_ms)
            continue
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("Benchmark latency results must contain QueryResult values or two-item tuples.")
        query_id, latency_ms = item
        if not isinstance(query_id, str):
            raise TypeError("Benchmark latency query IDs must be strings.")
        if not isinstance(latency_ms, int | float) or isinstance(latency_ms, bool):
            raise TypeError("Benchmark latency values must be numeric.")
        per_query_latencies[query_id] = float(latency_ms)
    return per_query_latencies


def _mean_or_none(values: Iterable[float]) -> float | None:
    numbers = tuple(values)
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    weight = position - lower_index
    return lower_value + (upper_value - lower_value) * weight
