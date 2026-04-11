from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snowiki.cli.commands.query import build_search_index, load_normalized_records
from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, PageSection
from snowiki.search import BM25SearchDocument, BM25SearchIndex, build_lexical_index
from snowiki.search.indexer import InvertedIndex, SearchDocument, SearchHit

from .contract import PHASE_1_THRESHOLDS
from .corpus import CANONICAL_BENCHMARK_FIXTURE_PATHS
from .latency import measure_latency
from .presets import BenchmarkPreset
from .quality import (
    SlicedQualitySummary,
    evaluate_quality_thresholds,
    evaluate_sliced_quality,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class BenchmarkQuery:
    query_id: str
    text: str
    group: str
    kind: str


@dataclass(frozen=True)
class CorpusBundle:
    records: tuple[dict[str, Any], ...]
    pages: tuple[dict[str, Any], ...]
    raw_index: InvertedIndex
    blended_index: InvertedIndex


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_queries(root: Path) -> tuple[BenchmarkQuery, ...]:
    del root
    payload = _load_json(_REPO_ROOT / "benchmarks" / "queries.json")
    rows = payload.get("queries", payload)
    if not isinstance(rows, list):
        raise ValueError("benchmarks/queries.json must contain a 'queries' list")
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
    payload = _load_json(_REPO_ROOT / "benchmarks" / "judgments.json")
    rows = payload.get("judgments", payload)
    if isinstance(rows, dict):
        return {str(key): [str(item) for item in value] for key, value in rows.items()}
    if isinstance(rows, list):
        return {
            str(row["query_id"]): [str(item) for item in row.get("relevant_paths", [])]
            for row in rows
        }
    raise ValueError(
        "benchmarks/judgments.json must contain a 'judgments' mapping or list rows"
    )


def _page_body(sections: list[PageSection]) -> str:
    return "\n\n".join(f"{section.title}\n{section.body}" for section in sections)


def _page_to_mapping(page: CompiledPage) -> dict[str, Any]:
    return {
        "id": page.path,
        "path": page.path,
        "title": page.title,
        "summary": page.summary,
        "body": _page_body(page.sections),
        "tags": page.tags,
        "related": page.related,
        "record_ids": page.record_ids,
        "updated_at": page.updated,
    }


def _build_corpus(root: Path) -> CorpusBundle:
    records = tuple(load_normalized_records(root))
    pages = (
        tuple(_page_to_mapping(page) for page in CompilerEngine(root).build_pages())
        if records
        else ()
    )
    raw = build_lexical_index(records).index
    blended, _, _ = build_search_index(root)
    return CorpusBundle(
        records=records,
        pages=pages,
        raw_index=raw,
        blended_index=blended,
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
        (_REPO_ROOT / relative_path).resolve().as_posix(): fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }


def _benchmark_fixture_digests() -> dict[str, str]:
    return {
        hashlib.sha256(
            (_REPO_ROOT / relative_path).read_bytes()
        ).hexdigest(): fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }


def _record_fixture_lookup(records: tuple[dict[str, Any], ...]) -> dict[str, str]:
    fixture_sources = _benchmark_fixture_sources()
    fixture_digests = _benchmark_fixture_digests()
    relative_lookup = {
        relative_path: fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }
    lookup: dict[str, str] = {}
    for payload in records:
        record_id = payload.get("id")
        if not isinstance(record_id, str):
            continue

        fixture_id: str | None = None
        path = payload.get("path")
        if isinstance(path, str):
            fixture_id = relative_lookup.get(path)

        metadata = payload.get("metadata")
        if fixture_id is None and isinstance(metadata, dict):
            source_path = metadata.get("source_path")
            if isinstance(source_path, str):
                fixture_id = fixture_sources.get(Path(source_path).resolve().as_posix())

        raw_ref = payload.get("raw_ref")
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
    pages: tuple[dict[str, Any], ...], record_lookup: dict[str, str]
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for page in pages:
        page_path = page.get("path")
        record_ids = page.get("record_ids")
        if not isinstance(page_path, str) or not isinstance(record_ids, list):
            continue
        fixture_ids = {
            record_lookup[record_id]
            for record_id in record_ids
            if isinstance(record_id, str) and record_id in record_lookup
        }
        if len(fixture_ids) == 1:
            lookup[page_path] = next(iter(fixture_ids))
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
    documents: tuple[SearchDocument, ...], *, use_kiwi_tokenizer: bool
) -> BM25SearchIndex:
    return BM25SearchIndex(
        [_bm25_document_from_search(document) for document in documents],
        use_kiwi_tokenizer=use_kiwi_tokenizer,
    )


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
    queries: tuple[BenchmarkQuery, ...],
    judgments: dict[str, list[str]],
    search_fn: Callable[[str], list[SearchHit]],
    hit_lookup: dict[str, str],
) -> dict[str, Any]:
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

    return {
        "name": name,
        "latency": latency.to_dict(),
        "quality": quality.to_dict(),
        "queries": {
            query_id: [
                {
                    "id": _hit_identifier(hit),
                    "path": hit.document.path,
                    "title": hit.document.title,
                    "score": round(hit.score, 6),
                }
                for hit in hits
            ]
            for query_id, hits in hits_by_query.items()
        },
    }


def run_baseline_comparison(
    root: Path,
    preset: BenchmarkPreset,
) -> dict[str, Any]:
    corpus = _build_corpus(root)
    judgments = _load_judgments(root)
    queries = tuple(
        query for query in _load_queries(root) if query.kind in preset.query_kinds
    )
    if not queries:
        raise ValueError(f"preset '{preset.name}' did not match any benchmark queries")

    raw_documents = tuple(corpus.raw_index.documents.values())
    hit_lookup = _benchmark_hit_lookup(corpus)
    bm25_plain_index = _build_bm25_index(raw_documents, use_kiwi_tokenizer=False)
    bm25_kiwi_index = _build_bm25_index(raw_documents, use_kiwi_tokenizer=True)

    results: dict[str, dict[str, Any]] = {}
    for baseline in preset.baselines:
        if baseline == "lexical":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: _run_lexical(
                    corpus.raw_index, query_text, preset.top_k
                ),
                hit_lookup=hit_lookup,
            )
            continue
        if baseline == "bm25s":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: [
                    _bm25_hit_to_search_hit(hit)
                    for hit in bm25_plain_index.search(query_text, limit=preset.top_k)
                ],
                hit_lookup=hit_lookup,
            )
            continue
        if baseline == "bm25s_kiwi":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: [
                    _bm25_hit_to_search_hit(hit)
                    for hit in bm25_kiwi_index.search(query_text, limit=preset.top_k)
                ],
                hit_lookup=hit_lookup,
            )
            continue
        raise ValueError(f"unsupported baseline: {baseline}")

    return {
        "preset": {
            "name": preset.name,
            "description": preset.description,
            "query_kinds": list(preset.query_kinds),
            "top_k": preset.top_k,
            "baselines": list(preset.baselines),
        },
        "corpus": {
            "records_indexed": len(corpus.records),
            "pages_indexed": len(corpus.pages),
            "raw_documents": corpus.raw_index.size,
            "blended_documents": corpus.blended_index.size,
            "queries_evaluated": len(queries),
        },
        "baselines": results,
    }
