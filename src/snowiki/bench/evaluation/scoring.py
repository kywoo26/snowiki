from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from snowiki.search.indexer import SearchDocument, SearchHit

from ..contract import BENCHMARK_THRESHOLDS
from ..reporting.models import (
    BaselineResult,
    BenchmarkHit,
    LatencyMetrics,
    PerQueryQuality,
    QualityMetrics,
    QualityReport,
    QualitySlices,
    QueryResult,
    ThresholdResult,
)
from ..runtime.latency import LatencySummary, measure_latency
from ..runtime.quality import (
    QualitySummary,
    QueryQualityResult,
    SlicedQualitySummary,
    evaluate_quality,
    evaluate_quality_thresholds,
    evaluate_sliced_quality,
)
from .qrels import BenchmarkQuery, QrelEntry, relevant_doc_ids


def _document_candidates(document: SearchDocument) -> set[str]:
    path_parts = Path(document.path).parts
    stem = Path(document.path).stem
    tokens = {stem, document.id, document.path, document.title}
    tokens.update(document.aliases)
    joined_parts = [part for part in path_parts if part and part not in {".", ".."}]
    if len(joined_parts) >= 2:
        tokens.add(f"{joined_parts[-2]}_{Path(joined_parts[-1]).stem}")

    normalized: set[str] = set()
    for token in tokens:
        lowered = str(token).strip().casefold()
        if not lowered:
            continue
        normalized.add(lowered)
        normalized.add(lowered.replace("-", "_"))
        normalized.add(lowered.replace("/", "_"))
        normalized.add(lowered.replace(" ", "_"))
    return normalized


def hit_identifier(hit: SearchHit) -> str:
    candidates = _document_candidates(hit.document)
    if hit.document.id.casefold() in candidates:
        return hit.document.id
    if hit.document.path.casefold() in candidates:
        return hit.document.path
    return hit.document.id


def _match_judgment(hit: SearchHit, relevant_ids: list[QrelEntry]) -> str:
    candidates = _document_candidates(hit.document)
    for relevant_id in relevant_ids:
        normalized = relevant_id.doc_id.casefold()
        if normalized in candidates:
            return relevant_id.doc_id
    return hit_identifier(hit)


def match_benchmark_hit(
    hit: SearchHit,
    relevant_ids: list[QrelEntry],
    hit_lookup: Mapping[str, str] | None,
) -> str:
    if hit_lookup is not None:
        fixture_id = hit_lookup.get(hit.document.id) or hit_lookup.get(hit.document.path)
        if fixture_id is not None:
            return fixture_id
    return _match_judgment(hit, relevant_ids)


def ranked_doc_ids(
    hits: list[SearchHit],
    relevant_ids: list[QrelEntry],
    *,
    hit_lookup: Mapping[str, str] | None = None,
) -> list[str]:
    ranked_ids: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        doc_id = match_benchmark_hit(hit, relevant_ids, hit_lookup)
        if doc_id in seen:
            continue
        ranked_ids.append(doc_id)
        seen.add(doc_id)
    return ranked_ids


def attach_threshold_report(summary: SlicedQualitySummary) -> SlicedQualitySummary:
    return SlicedQualitySummary(
        overall=summary.overall,
        by_group=summary.by_group,
        by_kind=summary.by_kind,
        by_subset=summary.by_subset,
        threshold_report=evaluate_quality_thresholds(
            summary,
            overall_thresholds=BENCHMARK_THRESHOLDS["overall"],
            slice_thresholds=BENCHMARK_THRESHOLDS["slices"],
        ),
    )


def latency_metrics(summary: LatencySummary) -> LatencyMetrics:
    return LatencyMetrics(
        p50_ms=summary.p50_ms,
        p95_ms=summary.p95_ms,
        mean_ms=summary.mean_ms,
        min_ms=summary.min_ms,
        max_ms=summary.max_ms,
    )


def quality_metrics(summary: QualitySummary) -> QualityMetrics:
    metrics_by_k = {
        metric: {str(k): value for k, value in values.items()}
        for metric, values in (summary.metrics_by_k or {}).items()
    }
    return QualityMetrics(
        recall_at_k=summary.recall_at_k,
        mrr=summary.mrr,
        ndcg_at_k=summary.ndcg_at_k,
        top_k=summary.top_k,
        top_ks=list(summary.top_ks),
        metrics_by_k=metrics_by_k,
        queries_evaluated=summary.queries_evaluated,
        per_query=[
            PerQueryQuality(
                query_id=item.query_id,
                ranked_ids=list(item.ranked_ids),
                relevant_ids=list(item.relevant_ids),
                tags=list(item.tags),
                no_answer=item.no_answer,
                recall_at_k=item.recall_at_k,
                reciprocal_rank=item.reciprocal_rank,
                ndcg_at_k=item.ndcg_at_k,
            )
            for item in summary.per_query
        ],
    )


def quality_report(summary: SlicedQualitySummary) -> QualityReport:
    return QualityReport(
        overall=quality_metrics(summary.overall),
        slices=QualitySlices(
            group={
                name: quality_metrics(metrics)
                for name, metrics in summary.by_group.items()
            },
            kind={
                name: quality_metrics(metrics)
                for name, metrics in summary.by_kind.items()
            },
            subset={
                name: quality_metrics(metrics)
                for name, metrics in (summary.by_subset or {}).items()
            },
        ),
        thresholds=[
            ThresholdResult(
                gate=entry.gate,
                metric=entry.metric,
                value=entry.value,
                delta=entry.delta,
                verdict=entry.verdict,
                threshold=entry.threshold,
                warnings=list(entry.warnings),
            )
            for entry in summary.threshold_report
        ],
    )


def query_result(query_id: str, hits: list[SearchHit]) -> QueryResult:
    return QueryResult(
        query_id=query_id,
        hits=[
            BenchmarkHit(
                id=hit_identifier(hit),
                path=hit.document.path,
                title=hit.document.title,
                score=round(hit.score, 6),
            )
            for hit in hits
        ],
    )


def evaluate_baseline(
    *,
    name: str,
    tokenizer_name: str | None = None,
    queries: tuple[BenchmarkQuery, ...],
    judgments: dict[str, list[QrelEntry]],
    search_fn: Callable[[str], list[SearchHit]],
    hit_lookup: Mapping[str, str] | None,
    top_ks: tuple[int, ...],
) -> BaselineResult:
    ranked_results: dict[str, list[str]] = {}
    hits_by_query: dict[str, list[SearchHit]] = {}
    relevant_ids = relevant_doc_ids(judgments)

    for query in queries:
        hits = list(search_fn(query.text))
        hits_by_query[query.query_id] = hits
        ranked_results[query.query_id] = ranked_doc_ids(
            hits,
            judgments.get(query.query_id, []),
            hit_lookup=hit_lookup,
        )

    latency = measure_latency(lambda item: search_fn(item.text), list(queries))
    quality = attach_threshold_report(
        evaluate_sliced_quality(
            ranked_results,
            relevant_ids,
            query_groups={query.query_id: query.group for query in queries},
            query_kinds={query.query_id: query.kind for query in queries},
            query_tags={query.query_id: query.tags for query in queries},
            query_no_answer={query.query_id: query.no_answer for query in queries},
            top_k=max((len(ranked) for ranked in ranked_results.values()), default=0) or 1,
            top_ks=top_ks,
        )
    )

    return BaselineResult(
        name=name,
        tokenizer_name=tokenizer_name,
        latency=latency_metrics(latency),
        quality=quality_report(quality),
        queries=[
            query_result(query_id, hits) for query_id, hits in hits_by_query.items()
        ],
    )


__all__ = [
    "QueryQualityResult",
    "QualitySummary",
    "SlicedQualitySummary",
    "attach_threshold_report",
    "evaluate_baseline",
    "evaluate_quality",
    "evaluate_quality_thresholds",
    "evaluate_sliced_quality",
    "hit_identifier",
    "match_benchmark_hit",
    "quality_metrics",
    "quality_report",
    "query_result",
    "ranked_doc_ids",
]
