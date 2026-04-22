from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from snowiki.search import BM25SearchIndex

from ..contract.presets import BenchmarkPreset, normalize_benchmark_baselines
from ..reporting.models import (
    BaselineResult,
    BenchmarkReport,
    CorpusSummary,
    PresetSummary,
)
from ..reporting.verdict import evaluate_candidate_policy
from .candidates import (
    assemble_candidate_matrix as _assemble_candidate_matrix,
)
from .candidates import (
    measure_operational_evidence as _measure_operational_evidence,
)
from .index import (
    benchmark_hit_lookup as _benchmark_hit_lookup,
)
from .index import (
    bm25_hit_to_search_hit as _bm25_hit_to_search_hit,
)
from .index import (
    build_bm25_index as _build_bm25_index,
)
from .index import (
    build_corpus as _build_corpus,
)
from .index import (
    run_lexical as _run_lexical,
)
from .index import (
    tokenizer_name_for_baseline as _tokenizer_name_for_baseline,
)
from .qrels import (
    load_judgments as _load_judgments,
)
from .qrels import (
    load_queries as _load_queries,
)
from .qrels import (
    normalize_qrels as _normalize_qrels,
)
from .qrels import (
    queries_from_payload as _queries_from_payload,
)
from .scoring import evaluate_baseline as _evaluate_baseline


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
        _load_queries(root) if queries_path is None else _load_queries(root, queries_path)
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
    raw_record_payloads = [record.model_dump(mode="python") for record in corpus.records]
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

    candidate_matrix = _assemble_candidate_matrix(
        results,
        operational_evidence=operational_evidence,
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
        candidate_matrix=candidate_matrix.model_copy(
            update={"decisions": list(evaluate_candidate_policy(candidate_matrix))}
        ),
    )


__all__ = ["run_baseline_comparison"]
