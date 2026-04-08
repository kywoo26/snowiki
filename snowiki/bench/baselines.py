from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snowiki.cli.commands.query import build_search_index, load_normalized_records
from snowiki.compiler.engine import CompilerEngine
from snowiki.compiler.taxonomy import CompiledPage, PageSection
from snowiki.search import build_lexical_index, topical_recall
from snowiki.search.indexer import InvertedIndex, SearchDocument, SearchHit

from .latency import measure_latency
from .presets import BenchmarkPreset
from .quality import evaluate_quality
from .semantic_slots import (
    SemanticSlotsConfig,
    expand_query_variants,
    semantic_slots_status,
)
from .token_reduction import compare_token_usage, summarize_token_usage


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
    payload = _load_json(root / "benchmarks" / "queries.json")
    rows = payload.get("queries", payload)
    if not isinstance(rows, list):
        raise ValueError("benchmarks/queries.json must contain a 'queries' list")
    queries: list[BenchmarkQuery] = []
    for row in rows:
        queries.append(
            BenchmarkQuery(
                query_id=str(row["id"]),
                text=str(row["text"]),
                group=str(row.get("group", "default")),
                kind=str(row.get("kind", "known-item")),
            )
        )
    return tuple(queries)


def _load_judgments(root: Path) -> dict[str, list[str]]:
    payload = _load_json(root / "benchmarks" / "judgments.json")
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


def _raw_context(hits: list[SearchHit]) -> str:
    return "\n\n".join(hit.document.content for hit in hits)


def _current_context(hits: list[SearchHit]) -> str:
    return "\n".join(
        f"{hit.document.title}: {hit.document.summary}".strip() for hit in hits
    )


def _v2_context(hits: list[SearchHit]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        line = f"{hit.document.title} | {hit.document.path} | {hit.document.summary}".strip()
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines)


def _run_raw(index: InvertedIndex, query: str, top_k: int) -> list[SearchHit]:
    return index.search(query, limit=top_k)


def _run_current(index: InvertedIndex, query: str, top_k: int) -> list[SearchHit]:
    return topical_recall(index, query, limit=top_k)


def _run_v2(
    index: InvertedIndex,
    query: str,
    top_k: int,
    semantic_slots: SemanticSlotsConfig,
) -> list[SearchHit]:
    merged: dict[str, SearchHit] = {}
    for variant in expand_query_variants(query, semantic_slots):
        for hit in topical_recall(index, variant, limit=max(top_k * 2, top_k)):
            existing = merged.get(hit.document.id)
            if existing is None or hit.score > existing.score:
                merged[hit.document.id] = hit
    ranked = sorted(
        merged.values(),
        key=lambda item: (-item.score, item.document.path, item.document.id),
    )
    return ranked[:top_k]


def _evaluate_baseline(
    *,
    name: str,
    queries: tuple[BenchmarkQuery, ...],
    judgments: dict[str, list[str]],
    search_fn: Any,
    context_fn: Any,
    semantic_slots: SemanticSlotsConfig,
) -> dict[str, Any]:
    ranked_results: dict[str, list[str]] = {}
    query_contexts: list[str] = []
    hits_by_query: dict[str, list[SearchHit]] = {}

    for query in queries:
        hits = list(search_fn(query.text))
        hits_by_query[query.query_id] = hits
        ranked_results[query.query_id] = [
            _match_judgment(hit, judgments.get(query.query_id, [])) for hit in hits
        ]
        query_contexts.append(context_fn(hits))

    latency = measure_latency(lambda item: search_fn(item.text), list(queries))
    quality = evaluate_quality(
        ranked_results,
        judgments,
        top_k=max((len(ranked) for ranked in ranked_results.values()), default=0) or 1,
    )
    return {
        "name": name,
        "latency": latency.to_dict(),
        "quality": quality.to_dict(),
        "token_usage": summarize_token_usage(query_contexts),
        "semantic_slots": semantic_slots_status(semantic_slots)
        if name == "v2"
        else semantic_slots_status(SemanticSlotsConfig(enabled=False)),
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
    *,
    semantic_slots: SemanticSlotsConfig,
) -> dict[str, Any]:
    corpus = _build_corpus(root)
    judgments = _load_judgments(root)
    queries = tuple(
        query for query in _load_queries(root) if query.kind in preset.query_kinds
    )
    if not queries:
        raise ValueError(f"preset '{preset.name}' did not match any benchmark queries")

    results: dict[str, dict[str, Any]] = {}
    for baseline in preset.baselines:
        if baseline == "raw":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: _run_raw(
                    corpus.raw_index, query_text, preset.top_k
                ),
                context_fn=_raw_context,
                semantic_slots=SemanticSlotsConfig(enabled=False),
            )
            continue
        if baseline == "current":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: _run_current(
                    corpus.blended_index, query_text, preset.top_k
                ),
                context_fn=_current_context,
                semantic_slots=SemanticSlotsConfig(enabled=False),
            )
            continue
        if baseline == "v2":
            results[baseline] = _evaluate_baseline(
                name=baseline,
                queries=queries,
                judgments=judgments,
                search_fn=lambda query_text: _run_v2(
                    corpus.blended_index, query_text, preset.top_k, semantic_slots
                ),
                context_fn=_v2_context,
                semantic_slots=semantic_slots,
            )
            continue
        raise ValueError(f"unsupported baseline: {baseline}")

    token_usage = {name: payload["token_usage"] for name, payload in results.items()}
    qualities = {
        name: {
            "recall_at_k": payload["quality"]["recall_at_k"],
            "mrr": payload["quality"]["mrr"],
            "ndcg_at_k": payload["quality"]["ndcg_at_k"],
        }
        for name, payload in results.items()
    }
    token_reduction = {
        name: summary.to_dict()
        for name, summary in compare_token_usage(token_usage, qualities).items()
    }
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
        "semantic_slots": semantic_slots_status(semantic_slots),
        "baselines": results,
        "token_reduction": token_reduction,
    }
