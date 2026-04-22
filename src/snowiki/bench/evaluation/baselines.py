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

from ..contract import PHASE_1_CORPUS, PHASE_1_THRESHOLDS
from ..contract.presets import (
    BenchmarkPreset,
    candidate_name_for_benchmark_baseline,
    normalize_benchmark_baseline,
    normalize_benchmark_baselines,
)
from ..reporting.models import (
    PAGE_LIST_ADAPTER,
    RECORD_LIST_ADAPTER,
    BaselineResult,
    BenchmarkHit,
    BenchmarkReport,
    CandidateMatrixEntry,
    CandidateMatrixReport,
    CandidateOperationalEvidence,
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
from ..reporting.verdict import evaluate_candidate_policy
from ..runtime.corpus import CANONICAL_BENCHMARK_FIXTURE_PATHS
from ..runtime.latency import LatencySummary, measure_latency
from ..runtime.operational import (
    measure_bm25_candidate_build,
    measure_regex_candidate_build,
)
from ..runtime.quality import (
    QualitySummary,
    SlicedQualitySummary,
    evaluate_quality_thresholds,
    evaluate_sliced_quality,
)
from .candidates import CANDIDATE_MATRIX, get_candidate


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
    tags: tuple[str, ...] = ()
    no_answer: bool = False


@dataclass(frozen=True)
class CorpusBundle:
    records: tuple[RecordModel, ...]
    pages: tuple[PageModel, ...]
    raw_index: InvertedIndex
    blended_index: InvertedIndex


@dataclass(frozen=True)
class QrelEntry:
    query_id: str
    doc_id: str
    relevance: int = 1


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


def _resolve_benchmark_asset_path(
    root: Path, configured_path: str | Path | None, *, default_relative_path: str
) -> tuple[Path, str]:
    raw_path = configured_path or default_relative_path
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate, candidate.as_posix()
    root_candidate = root / candidate
    if root_candidate.exists():
        return root_candidate, root_candidate.as_posix()
    return resolve_repo_asset_path(candidate.as_posix()), candidate.as_posix()


def _queries_from_payload(
    payload: object, *, path_label: str
) -> tuple[BenchmarkQuery, ...]:
    rows = _require_mapping_rows(
        _mapping_rows(payload, "queries"),
        label=f"{path_label} must contain a 'queries' list",
    )
    return tuple(
        BenchmarkQuery(
            query_id=str(row["id"]),
            text=str(row["text"]),
            group=str(row.get("group", "default")),
            kind=str(row.get("kind", "known-item")),
            tags=tuple(
                _string_list(
                    row.get("tags", []),
                    label=f"{path_label} tags must be a list",
                )
            ),
            no_answer=bool(row.get("no_answer", False)),
        )
        for row in rows
    )


def _load_queries(
    root: Path, queries_path: str | Path | None = None
) -> tuple[BenchmarkQuery, ...]:
    resolved_path, path_label = _resolve_benchmark_asset_path(
        root,
        queries_path,
        default_relative_path=PHASE_1_CORPUS["queries"],
    )
    payload = _load_json(resolved_path)
    return _queries_from_payload(payload, path_label=path_label)


def _parse_qrel_entry(query_id: str, value: object, *, label: str) -> QrelEntry:
    if isinstance(value, QrelEntry):
        return value
    if isinstance(value, str):
        return QrelEntry(query_id=query_id, doc_id=value)
    if not isinstance(value, Mapping):
        raise ValueError(label)
    row = cast(Mapping[str, object], value)

    row_query_id = row.get("query_id", query_id)
    if str(row_query_id) != query_id:
        raise ValueError(label)

    doc_id = row.get("doc_id")
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise ValueError(label)

    relevance_raw = row.get("relevance", 1)
    if isinstance(relevance_raw, bool):
        relevance = int(relevance_raw)
    elif isinstance(relevance_raw, int):
        relevance = relevance_raw
    elif isinstance(relevance_raw, str):
        try:
            relevance = int(relevance_raw)
        except ValueError as exc:
            raise ValueError(label) from exc
    else:
        raise ValueError(label)

    return QrelEntry(query_id=query_id, doc_id=doc_id, relevance=relevance)


def _parse_qrel_entries(query_id: str, values: object, *, label: str) -> list[QrelEntry]:
    if not isinstance(values, list):
        raise ValueError(label)
    return [_parse_qrel_entry(query_id, value, label=label) for value in values]


def load_qrels(path: Path) -> dict[str, list[QrelEntry]]:
    payload = _load_json(path)
    rows = _mapping_rows(payload, "judgments")
    label = f"{path.as_posix()} must contain a 'judgments' mapping or list rows"
    if isinstance(rows, Mapping):
        return {
            str(key): _parse_qrel_entries(str(key), value, label=label)
            for key, value in rows.items()
        }
    if isinstance(rows, list):
        mapping_rows = _require_mapping_rows(rows, label=label)
        qrels: dict[str, list[QrelEntry]] = {}
        for row in mapping_rows:
            query_id = str(row["query_id"])
            if "doc_id" in row:
                qrels.setdefault(query_id, []).append(
                    _parse_qrel_entry(query_id, row, label=label)
                )
                continue

            if "qrels" in row:
                qrels.setdefault(query_id, []).extend(
                    _parse_qrel_entries(query_id, row["qrels"], label=label)
                )
                continue

            qrels.setdefault(query_id, []).extend(
                QrelEntry(query_id=query_id, doc_id=doc_id)
                for doc_id in _string_list(row.get("relevant_paths", []), label=label)
            )
        return qrels
    raise ValueError(label)


def _load_judgments(
    root: Path, judgments_path: str | Path | None = None
) -> dict[str, list[QrelEntry]]:
    resolved_path, path_label = _resolve_benchmark_asset_path(
        root,
        judgments_path,
        default_relative_path=PHASE_1_CORPUS["judgments"],
    )
    try:
        return load_qrels(resolved_path)
    except ValueError as exc:
        raise ValueError(
            f"{path_label} must contain a 'judgments' mapping or list rows"
        ) from exc


def _normalize_qrels(
    judgments: Mapping[str, object], *, label: str = "judgments"
) -> dict[str, list[QrelEntry]]:
    return {
        str(query_id): _parse_qrel_entries(
            str(query_id),
            entries,
            label=f"{label} must map query ids to qrel lists",
        )
        for query_id, entries in judgments.items()
    }


def _relevant_doc_ids(judgments: Mapping[str, list[QrelEntry]]) -> dict[str, list[str]]:
    return {
        query_id: [qrel.doc_id for qrel in qrels if qrel.relevance > 0]
        for query_id, qrels in judgments.items()
    }


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


def _match_judgment(hit: SearchHit, relevant_ids: list[QrelEntry]) -> str:
    candidates = _document_candidates(hit.document)
    for relevant_id in relevant_ids:
        normalized = relevant_id.doc_id.casefold()
        if normalized in candidates:
            return relevant_id.doc_id
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
    hit: SearchHit,
    relevant_ids: list[QrelEntry],
    hit_lookup: Mapping[str, str] | None,
) -> str:
    if hit_lookup is not None:
        fixture_id = hit_lookup.get(hit.document.id) or hit_lookup.get(hit.document.path)
        if fixture_id is not None:
            return fixture_id
    return _match_judgment(hit, relevant_ids)


def _ranked_doc_ids(
    hits: list[SearchHit],
    relevant_ids: list[QrelEntry],
    *,
    hit_lookup: Mapping[str, str] | None = None,
) -> list[str]:
    ranked_ids: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        doc_id = _match_benchmark_hit(hit, relevant_ids, hit_lookup)
        if doc_id in seen:
            continue
        ranked_ids.append(doc_id)
        seen.add(doc_id)
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
    if normalized_baseline.startswith("bm25s_kiwi") or normalized_baseline in {
        "bm25s_hf_wordpiece",
        "bm25s_mecab_full",
    }:
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
    judgments: dict[str, list[QrelEntry]],
    search_fn: Callable[[str], list[SearchHit]],
    hit_lookup: Mapping[str, str] | None,
    top_ks: tuple[int, ...],
) -> BaselineResult:
    ranked_results: dict[str, list[str]] = {}
    hits_by_query: dict[str, list[SearchHit]] = {}
    relevant_doc_ids = _relevant_doc_ids(judgments)

    for query in queries:
        hits = list(search_fn(query.text))
        hits_by_query[query.query_id] = hits
        ranked_results[query.query_id] = _ranked_doc_ids(
            hits,
            judgments.get(query.query_id, []),
            hit_lookup=hit_lookup,
        )

    latency = measure_latency(lambda item: search_fn(item.text), list(queries))
    quality = _attach_threshold_report(
        evaluate_sliced_quality(
            ranked_results,
            relevant_doc_ids,
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
        top_ks=list(summary.top_ks),
        metrics_by_k={metric: {str(k): value for k, value in values.items()} for metric, values in (summary.metrics_by_k or {}).items()},
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
            subset={
                name: _quality_metrics(metrics)
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
    *,
    operational_evidence: Mapping[str, CandidateOperationalEvidence] | None = None,
) -> CandidateMatrixReport:
    candidates: list[CandidateMatrixEntry] = []
    evidence_map = operational_evidence or {}

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
                operational_evidence=evidence_map.get(
                    candidate.candidate_name, candidate.operational_evidence
                ),
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
                operational_evidence=evidence_map.get(
                    candidate.candidate_name, candidate.operational_evidence
                ),
            )
        )

    matrix = CandidateMatrixReport(candidates=candidates)
    return matrix.model_copy(
        update={"decisions": list(evaluate_candidate_policy(matrix))}
    )


def run_baseline_comparison(
    root: Path,
    preset: BenchmarkPreset,
    *,
    queries_path: str | Path | None = None,
    judgments_path: str | Path | None = None,
    queries_data: object | None = None,
    judgments_data: Mapping[str, object] | None = None,
    use_generic_scoring: bool = False,
) -> BenchmarkReport:
    corpus = _build_corpus(root)
    loaded_judgments = (
        _load_judgments(root)
        if judgments_path is None
        else _load_judgments(root, judgments_path)
    )
    if judgments_data is not None:
        loaded_judgments = judgments_data
    judgments = _normalize_qrels(
        loaded_judgments,
        label=(
            "inline benchmark judgments must map query ids to qrel lists"
            if judgments_data is not None
            else "judgments"
        ),
    )
    loaded_queries = (
        _load_queries(root)
        if queries_path is None
        else _load_queries(root, queries_path)
    )
    if queries_data is not None:
        loaded_queries = _queries_from_payload(
            queries_data,
            path_label="inline benchmark queries",
        )
    queries = tuple(
        query for query in loaded_queries if query.kind in preset.query_kinds
    )
    if not queries:
        raise ValueError(f"preset '{preset.name}' did not match any benchmark queries")

    raw_documents = tuple(corpus.raw_index.documents.values())
    raw_record_payloads = [
        record.model_dump(mode="python") for record in corpus.records
    ]
    hit_lookup = None if use_generic_scoring else _benchmark_hit_lookup(corpus)
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
                top_ks=preset.top_ks,
            )
            continue
        if baseline == "bm25s" or baseline.startswith("bm25s_"):
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
                top_ks=preset.top_ks,
            )
            continue
        raise ValueError(f"unsupported baseline: {baseline}")

    operational_evidence = _measure_operational_evidence(
        records=raw_record_payloads,
        bm25_indexes=bm25_indexes,
    )

    return BenchmarkReport(
        preset=PresetSummary(
            name=preset.name,
            description=preset.description,
            query_kinds=list(preset.query_kinds),
            top_k=preset.top_k,
            top_ks=list(preset.top_ks),
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
        candidate_matrix=_assemble_candidate_matrix(
            results, operational_evidence=operational_evidence
        ),
    )


def _with_measured_operational_evidence(
    candidate_name: str,
    *,
    memory_peak_rss_mb: float | None,
    disk_size_mb: float,
) -> CandidateOperationalEvidence:
    candidate = get_candidate(candidate_name)
    base = candidate.operational_evidence
    return base.model_copy(
        update={
            "memory_peak_rss_mb": memory_peak_rss_mb,
            "memory_evidence_status": (
                "measured" if memory_peak_rss_mb is not None else "not_measured"
            ),
            "disk_size_mb": disk_size_mb,
            "disk_size_evidence_status": "measured",
        }
    )


def _measure_operational_evidence(
    *,
    records: list[dict[str, object]],
    bm25_indexes: Mapping[str, object],
) -> dict[str, CandidateOperationalEvidence]:
    evidence: dict[str, CandidateOperationalEvidence] = {}
    regex_peak_rss_mb, regex_disk_size_mb = measure_regex_candidate_build(
        records=records
    )
    evidence["regex_v1"] = _with_measured_operational_evidence(
        "regex_v1",
        memory_peak_rss_mb=regex_peak_rss_mb,
        disk_size_mb=regex_disk_size_mb,
    )

    for tokenizer_name, bm25_index in bm25_indexes.items():
        if not isinstance(bm25_index, BM25SearchIndex):
            continue
        peak_rss_mb, disk_size_mb = measure_bm25_candidate_build(
            documents=bm25_index.documents,
            tokenizer_name=tokenizer_name,
        )
        evidence[tokenizer_name] = _with_measured_operational_evidence(
            tokenizer_name,
            memory_peak_rss_mb=peak_rss_mb,
            disk_size_mb=disk_size_mb,
        )
    return evidence
