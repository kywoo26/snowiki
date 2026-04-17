from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from snowiki.compiler.engine import CompilerEngine
from snowiki.config import resolve_repo_asset_path
from snowiki.search import BM25SearchDocument, BM25SearchIndex, build_lexical_index
from snowiki.search.indexer import InvertedIndex, SearchDocument, SearchHit
from snowiki.search.registry import resolve_legacy_tokenizer
from snowiki.search.workspace import (
    RetrievalService,
    compiled_page_to_search_mapping,
    load_normalized_records,
)

from .contract import PHASE_1_THRESHOLDS
from .corpus import CANONICAL_BENCHMARK_FIXTURE_PATHS
from .latency import LatencySummary, measure_latency
from .matrix import CANDIDATE_MATRIX, get_candidate
from .models import (
    PAGE_LIST_ADAPTER,
    RECORD_LIST_ADAPTER,
    BaselineResult,
    BenchmarkHit,
    BenchmarkReport,
    CandidateMatrixEntry,
    CandidateMatrixReport,
    CorpusSummary,
    LatencyMetrics,
    PageModel,
    PerQueryQuality,
    PresetSummary,
    QualityMetrics,
    QualityReport,
    QualitySlices,
    QueryResult,
    RecordModel,
    ThresholdResult,
)
from .presets import (
    BenchmarkPreset,
    candidate_name_for_benchmark_baseline,
    normalize_benchmark_baseline,
    normalize_benchmark_baselines,
)
from .quality import (
    QualitySummary,
    SlicedQualitySummary,
    evaluate_quality_thresholds,
    evaluate_sliced_quality,
)
from .verdict import evaluate_candidate_policy


class _Bm25DocumentLike(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def path(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def content(self) -> str: ...

    @property
    def summary(self) -> str: ...

    @property
    def aliases(self) -> tuple[str, ...]: ...

    @property
    def recorded_at(self) -> datetime | None: ...

    @property
    def source_type(self) -> str: ...


class _Bm25HitLike(Protocol):
    @property
    def document(self) -> _Bm25DocumentLike: ...

    @property
    def score(self) -> float: ...

    @property
    def matched_terms(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class BenchmarkQuery:
    query_id: str
    text: str
    group: str
    kind: str


@dataclass(frozen=True)
class CorpusBundle:
    records: tuple[RecordModel, ...]
    pages: tuple[PageModel, ...]
    raw_index: InvertedIndex
    blended_index: InvertedIndex


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping_rows(payload: object, key: str) -> object:
    if isinstance(payload, dict):
        payload_map = cast(dict[str, object], payload)
        return payload_map.get(key, payload)
    return payload


def _require_mapping_rows(rows: object, *, label: str) -> list[Mapping[str, object]]:
    if not isinstance(rows, list):
        raise ValueError(label)
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError(label)
    return [cast(Mapping[str, object], row) for row in rows]


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label)
    return [str(item) for item in value]


def _load_queries(root: Path) -> tuple[BenchmarkQuery, ...]:
    del root
    payload = _load_json(resolve_repo_asset_path("benchmarks/queries.json"))
    rows = _require_mapping_rows(
        _mapping_rows(payload, "queries"),
        label="benchmarks/queries.json must contain a 'queries' list",
    )
    return tuple(
        BenchmarkQuery(
            query_id=str(row["id"]),
            text=str(row["text"]),
            group=str(row.get("group", "default")),
            kind=str(row.get("kind", "known-item")),
        )
        for row in rows
    )


def _load_judgments(root: Path) -> dict[str, list[str]]:
    del root
    payload = _load_json(resolve_repo_asset_path("benchmarks/judgments.json"))
    rows = _mapping_rows(payload, "judgments")
    if isinstance(rows, Mapping):
        return {
            str(key): _string_list(
                value,
                label=(
                    "benchmarks/judgments.json must contain a 'judgments' mapping or list rows"
                ),
            )
            for key, value in rows.items()
        }
    if isinstance(rows, list):
        mapping_rows = _require_mapping_rows(
            rows,
            label=(
                "benchmarks/judgments.json must contain a 'judgments' mapping or list rows"
            ),
        )
        return {
            str(row["query_id"]): _string_list(
                row.get("relevant_paths", []),
                label=(
                    "benchmarks/judgments.json must contain a 'judgments' mapping or list rows"
                ),
            )
            for row in mapping_rows
        }
    raise ValueError(
        "benchmarks/judgments.json must contain a 'judgments' mapping or list rows"
    )


def _build_corpus(root: Path) -> CorpusBundle:
    records = tuple(RECORD_LIST_ADAPTER.validate_python(load_normalized_records(root)))
    pages = (
        tuple(
            PAGE_LIST_ADAPTER.validate_python(
                [
                    compiled_page_to_search_mapping(page)
                    for page in CompilerEngine(root).build_pages()
                ]
            )
        )
        if records
        else ()
    )
    raw = build_lexical_index(
        record.model_dump(mode="python") for record in records
    ).index
    blended_snapshot = RetrievalService.from_records_and_pages(
        records=[record.model_dump(mode="python") for record in records],
        pages=[page.model_dump(mode="python") for page in pages],
    )
    return CorpusBundle(
        records=records,
        pages=pages,
        raw_index=raw,
        blended_index=blended_snapshot.index,
    )


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


def _hit_identifier(hit: SearchHit) -> str:
    candidates = _document_candidates(hit.document)
    if hit.document.id.casefold() in candidates:
        return hit.document.id
    if hit.document.path.casefold() in candidates:
        return hit.document.path
    return hit.document.id


def _match_judgment(hit: SearchHit, relevant_ids: list[str]) -> str:
    candidates = _document_candidates(hit.document)
    for relevant_id in relevant_ids:
        normalized = str(relevant_id).casefold()
        if normalized in candidates:
            return str(relevant_id)
    return _hit_identifier(hit)


def _benchmark_fixture_sources() -> dict[str, str]:
    return {
        resolve_repo_asset_path(relative_path).resolve().as_posix(): fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }


def _benchmark_fixture_digests() -> dict[str, str]:
    return {
        hashlib.sha256(
            resolve_repo_asset_path(relative_path).read_bytes()
        ).hexdigest(): fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }


def _record_fixture_lookup(records: tuple[RecordModel, ...]) -> dict[str, str]:
    fixture_sources = _benchmark_fixture_sources()
    fixture_digests = _benchmark_fixture_digests()
    relative_lookup = {
        relative_path: fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }
    lookup: dict[str, str] = {}
    for payload in records:
        record_id = payload.id
        fixture_id: str | None = None
        path = payload.path
        if path is not None:
            fixture_id = relative_lookup.get(path)

        metadata = payload.metadata
        if fixture_id is None:
            source_path = metadata.get("source_path")
            if isinstance(source_path, str):
                fixture_id = fixture_sources.get(Path(source_path).resolve().as_posix())

        raw_ref = payload.raw_ref
        if fixture_id is None and isinstance(raw_ref, dict):
            sha256 = raw_ref.get("sha256")
            if isinstance(sha256, str):
                fixture_id = fixture_digests.get(sha256)

        if fixture_id is not None:
            lookup[record_id] = fixture_id
            if isinstance(path, str):
                lookup[path] = fixture_id
    return lookup


def _page_fixture_lookup(
    pages: tuple[PageModel, ...], record_lookup: dict[str, str]
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for page in pages:
        fixture_ids = {
            record_lookup[record_id]
            for record_id in page.record_ids
            if record_id in record_lookup
        }
        if len(fixture_ids) == 1:
            lookup[page.path] = next(iter(fixture_ids))
    return lookup


def _benchmark_hit_lookup(corpus: CorpusBundle) -> dict[str, str]:
    record_lookup = _record_fixture_lookup(corpus.records)
    return {**record_lookup, **_page_fixture_lookup(corpus.pages, record_lookup)}


def _match_benchmark_hit(
    hit: SearchHit, relevant_ids: list[str], hit_lookup: dict[str, str]
) -> str:
    fixture_id = hit_lookup.get(hit.document.id) or hit_lookup.get(hit.document.path)
    if fixture_id is not None:
        return fixture_id
    return _match_judgment(hit, relevant_ids)


def _ranked_fixture_ids(
    hits: list[SearchHit],
    relevant_ids: list[str],
    *,
    hit_lookup: dict[str, str],
) -> list[str]:
    ranked_ids: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        fixture_id = _match_benchmark_hit(hit, relevant_ids, hit_lookup)
        if fixture_id in seen:
            continue
        ranked_ids.append(fixture_id)
        seen.add(fixture_id)
    return ranked_ids


def _run_lexical(index: InvertedIndex, query: str, top_k: int) -> list[SearchHit]:
    return index.search(query, limit=top_k)


def _bm25_document_from_search(document: SearchDocument) -> BM25SearchDocument:
    return BM25SearchDocument(
        id=document.id,
        path=document.path,
        kind=document.kind,
        title=document.title,
        content=document.content,
        summary=document.summary,
        aliases=document.aliases,
        recorded_at=document.recorded_at,
        source_type=document.source_type,
    )


def _bm25_hit_to_search_hit(hit: Any) -> SearchHit:
    return SearchHit(
        document=SearchDocument(
            id=hit.document.id,
            path=hit.document.path,
            kind=hit.document.kind,
            title=hit.document.title,
            content=hit.document.content,
            summary=hit.document.summary,
            aliases=hit.document.aliases,
            recorded_at=hit.document.recorded_at,
            source_type=hit.document.source_type,
        ),
        score=float(hit.score),
        matched_terms=tuple(hit.matched_terms),
    )


def _build_bm25_index(
    documents: tuple[SearchDocument, ...],
    *,
    tokenizer_name: str,
) -> BM25SearchIndex:
    return BM25SearchIndex(
        [_bm25_document_from_search(document) for document in documents],
        tokenizer_name=tokenizer_name,
    )


def _tokenizer_name_for_baseline(baseline: str) -> str:
    normalized_baseline = normalize_benchmark_baseline(baseline)
    if normalized_baseline == "bm25s":
        resolved = resolve_legacy_tokenizer(use_kiwi_tokenizer=False)
        if resolved is None:
            raise ValueError(f"could not resolve tokenizer for baseline: {baseline}")
        return resolved
    if normalized_baseline.startswith("bm25s_kiwi"):
        resolved = resolve_legacy_tokenizer(benchmark_alias=normalized_baseline)
        if resolved is None:
            raise ValueError(f"unsupported baseline: {baseline}")
        return resolved
    raise ValueError(f"unsupported baseline: {baseline}")


def _attach_threshold_report(summary: SlicedQualitySummary) -> SlicedQualitySummary:
    return SlicedQualitySummary(
        overall=summary.overall,
        by_group=summary.by_group,
        by_kind=summary.by_kind,
        threshold_report=evaluate_quality_thresholds(
            summary,
            overall_thresholds=PHASE_1_THRESHOLDS["overall"],
            slice_thresholds=PHASE_1_THRESHOLDS["slices"],
        ),
    )


def _evaluate_baseline(
    *,
    name: str,
    tokenizer_name: str | None = None,
    queries: tuple[BenchmarkQuery, ...],
    judgments: dict[str, list[str]],
    search_fn: Callable[[str], list[SearchHit]],
    hit_lookup: dict[str, str],
) -> BaselineResult:
    ranked_results: dict[str, list[str]] = {}
    hits_by_query: dict[str, list[SearchHit]] = {}

    for query in queries:
        hits = list(search_fn(query.text))
        hits_by_query[query.query_id] = hits
        ranked_results[query.query_id] = _ranked_fixture_ids(
            hits,
            judgments.get(query.query_id, []),
            hit_lookup=hit_lookup,
        )

    latency = measure_latency(lambda item: search_fn(item.text), list(queries))
    quality = _attach_threshold_report(
        evaluate_sliced_quality(
            ranked_results,
            judgments,
            query_groups={query.query_id: query.group for query in queries},
            query_kinds={query.query_id: query.kind for query in queries},
            top_k=max((len(ranked) for ranked in ranked_results.values()), default=0)
            or 1,
        )
    )

    return BaselineResult(
        name=name,
        tokenizer_name=tokenizer_name,
        latency=_latency_metrics(latency),
        quality=_quality_report(quality),
        queries=[
            _query_result(query_id, hits) for query_id, hits in hits_by_query.items()
        ],
    )


def _latency_metrics(summary: LatencySummary) -> LatencyMetrics:
    return LatencyMetrics(
        p50_ms=summary.p50_ms,
        p95_ms=summary.p95_ms,
        mean_ms=summary.mean_ms,
        min_ms=summary.min_ms,
        max_ms=summary.max_ms,
    )


def _quality_metrics(summary: QualitySummary) -> QualityMetrics:
    return QualityMetrics(
        recall_at_k=summary.recall_at_k,
        mrr=summary.mrr,
        ndcg_at_k=summary.ndcg_at_k,
        top_k=summary.top_k,
        queries_evaluated=summary.queries_evaluated,
        per_query=[
            PerQueryQuality(
                query_id=item.query_id,
                ranked_ids=list(item.ranked_ids),
                relevant_ids=list(item.relevant_ids),
                recall_at_k=item.recall_at_k,
                reciprocal_rank=item.reciprocal_rank,
                ndcg_at_k=item.ndcg_at_k,
            )
            for item in summary.per_query
        ],
    )


def _quality_report(summary: SlicedQualitySummary) -> QualityReport:
    return QualityReport(
        overall=_quality_metrics(summary.overall),
        slices=QualitySlices(
            group={
                name: _quality_metrics(metrics)
                for name, metrics in summary.by_group.items()
            },
            kind={
                name: _quality_metrics(metrics)
                for name, metrics in summary.by_kind.items()
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


def _query_result(query_id: str, hits: list[SearchHit]) -> QueryResult:
    return QueryResult(
        query_id=query_id,
        hits=[
            BenchmarkHit(
                id=_hit_identifier(hit),
                path=hit.document.path,
                title=hit.document.title,
                score=round(hit.score, 6),
            )
            for hit in hits
        ],
    )


def _assemble_candidate_matrix(
    baseline_results: Mapping[str, BaselineResult],
) -> CandidateMatrixReport:
    candidates: list[CandidateMatrixEntry] = []

    for evidence_baseline, baseline_result in baseline_results.items():
        candidate = get_candidate(
            candidate_name_for_benchmark_baseline(evidence_baseline)
        )
        candidates.append(
            CandidateMatrixEntry(
                candidate_name=candidate.candidate_name,
                evidence_baseline=evidence_baseline,
                role=candidate.role,
                admission_status=candidate.admission_status,
                control=candidate.control,
                operational_evidence=candidate.operational_evidence,
                baseline=baseline_result,
            )
        )

    for candidate in CANDIDATE_MATRIX:
        if candidate.evidence_baseline is not None:
            continue
        candidates.append(
            CandidateMatrixEntry(
                candidate_name=candidate.candidate_name,
                evidence_baseline=candidate.evidence_baseline,
                role=candidate.role,
                admission_status=candidate.admission_status,
                control=candidate.control,
                operational_evidence=candidate.operational_evidence,
            )
        )

    matrix = CandidateMatrixReport(candidates=candidates)
    return matrix.model_copy(
        update={"decisions": list(evaluate_candidate_policy(matrix))}
    )


def run_baseline_comparison(
    root: Path,
    preset: BenchmarkPreset,
) -> BenchmarkReport:
    corpus = _build_corpus(root)
    judgments = _load_judgments(root)
    queries = tuple(
        query for query in _load_queries(root) if query.kind in preset.query_kinds
    )
    if not queries:
        raise ValueError(f"preset '{preset.name}' did not match any benchmark queries")

    raw_documents = tuple(corpus.raw_index.documents.values())
    hit_lookup = _benchmark_hit_lookup(corpus)
    normalized_baselines = normalize_benchmark_baselines(preset.baselines)
    bm25_indexes: dict[str, BM25SearchIndex] = {}

    results: dict[str, BaselineResult] = {}
    for baseline in normalized_baselines:
        if baseline == "lexical":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                tokenizer_name="regex_v1",
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: _run_lexical(
                    corpus.raw_index, query_text, preset.top_k
                ),
                hit_lookup=hit_lookup,
            )
            continue
        if baseline == "bm25s" or baseline.startswith("bm25s_kiwi"):
            tokenizer_name = _tokenizer_name_for_baseline(baseline)
            if tokenizer_name not in bm25_indexes:
                bm25_indexes[tokenizer_name] = _build_bm25_index(
                    raw_documents,
                    tokenizer_name=tokenizer_name,
                )
            current_index = bm25_indexes[tokenizer_name]
            results[baseline] = _evaluate_baseline(
                name=baseline,
                tokenizer_name=tokenizer_name,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text, bm25_index=current_index: [
                    _bm25_hit_to_search_hit(hit)
                    for hit in bm25_index.search(query_text, limit=preset.top_k)
                ],
                hit_lookup=hit_lookup,
            )
            continue
        raise ValueError(f"unsupported baseline: {baseline}")

    return BenchmarkReport(
        preset=PresetSummary(
            name=preset.name,
            description=preset.description,
            query_kinds=list(preset.query_kinds),
            top_k=preset.top_k,
            baselines=list(normalized_baselines),
        ),
        corpus=CorpusSummary(
            records_indexed=len(corpus.records),
            pages_indexed=len(corpus.pages),
            raw_documents=corpus.raw_index.size,
            blended_documents=corpus.blended_index.size,
            queries_evaluated=len(queries),
        ),
        baselines=results,
        candidate_matrix=_assemble_candidate_matrix(results),
    )
