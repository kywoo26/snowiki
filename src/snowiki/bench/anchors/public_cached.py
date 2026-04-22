from __future__ import annotations

import csv
import gzip
import json
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Final, Literal, cast

from snowiki.bench.corpus import BenchmarkCorpusManifest
from snowiki.bench.datasets import (
    BenchmarkDatasetFetchResult,
    BenchmarkDatasetId,
    BenchmarkDatasetSourceFetch,
    get_benchmark_dataset_spec,
    get_benchmark_materialized_root,
    resolve_cached_benchmark_dataset,
)
from snowiki.bench.models import BenchmarkAssetManifest, BenchmarkProvenance

PublicAnchorSampleMode = Literal["quick", "standard", "full"]

QUICK_SIZE: Final[int] = 200
STANDARD_SIZE: Final[int] = 500
FULL_CAP: Final[int] = 1000
_MAX_IMPORTED_TITLE_LENGTH: Final[int] = 96
_WIKILINK_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[\[([^\[\]]+)\]\]")
_TEMPLATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{\{([^{}]+)\}\}")
_MEDIA_NAMESPACE_PREFIXES: Final[tuple[str, ...]] = (
    "file:",
    "image:",
    "category:",
    "media:",
    "파일:",
    "이미지:",
    "분류:",
)
_PUBLIC_DATASET_METADATA: Final[dict[BenchmarkDatasetId, dict[str, str]]] = {
    "ms_marco_passage": {
        "name": "MS MARCO Passage Ranking",
        "description": "Classic passage-retrieval benchmark from Bing logs.",
    },
    "trec_dl_2019_passage": {
        "name": "TREC DL 2019 Passage",
        "description": "NIST judged passage ranking track on MS MARCO.",
    },
    "trec_dl_2020_passage": {
        "name": "TREC DL 2020 Passage",
        "description": "NIST judged passage ranking track on MS MARCO.",
    },
    "miracl_ko": {
        "name": "MIRACL Korean",
        "description": "Deterministic manifest sampled from the real cached MIRACL Korean public benchmark assets.",
    },
    "miracl_en": {
        "name": "MIRACL English",
        "description": "Deterministic manifest sampled from the real cached MIRACL English public benchmark assets.",
    },
    "miracl_ja": {
        "name": "MIRACL Japanese",
        "description": "Deterministic manifest sampled from the real cached MIRACL Japanese public benchmark assets.",
    },
    "miracl_zh": {
        "name": "MIRACL Chinese",
        "description": "Deterministic manifest sampled from the real cached MIRACL Chinese public benchmark assets.",
    },
    "mr_tydi_ko": {
        "name": "Mr. TyDi Korean",
        "description": "Deterministic manifest sampled from the real cached Mr. TyDi Korean public benchmark assets.",
    },
    "beir_nq": {
        "name": "BEIR Natural Questions",
        "description": "Deterministic manifest sampled from the real cached BEIR NQ public benchmark assets.",
    },
    "beir_scifact": {
        "name": "BEIR SciFact",
        "description": "Deterministic manifest sampled from the real cached BEIR SciFact public benchmark assets.",
    },
    "beir_fiqa_2018": {
        "name": "BEIR FiQA 2018",
        "description": "Deterministic manifest sampled from the real cached BEIR FiQA public benchmark assets.",
    },
    "beir_arguana": {
        "name": "BEIR ArguAna",
        "description": "Deterministic manifest sampled from the real cached BEIR ArguAna public benchmark assets.",
    },
    "beir_nfcorpus": {
        "name": "BEIR NFCorpus",
        "description": "Deterministic manifest sampled from the real cached BEIR NFCorpus public benchmark assets.",
    },
}


def resolve_public_anchor_sample_count(
    query_count: int,
    mode: PublicAnchorSampleMode,
    explicit_size: int | None = None,
) -> int:
    if explicit_size is not None:
        if explicit_size < 1:
            raise ValueError("public anchor sample size must be at least 1")
        return min(explicit_size, query_count)
    if mode == "quick":
        return min(QUICK_SIZE, query_count)
    if mode == "standard":
        return min(STANDARD_SIZE, query_count)
    return min(query_count, FULL_CAP)


def _load_miracl_cached_manifest(
    dataset_id: BenchmarkDatasetId,
    language_code: str,
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MIRACL benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset(dataset_id, data_root=data_root)
    dataset_source = _require_source(fetched, "dataset")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(
        dataset_source.snapshot_path, f"{language_code}-corpus/*.parquet", cache_dir
    )
    query_rows = _load_parquet_rows(
        dataset_source.snapshot_path, f"{language_code}-queries/*.parquet", cache_dir
    )
    qrel_rows = _load_parquet_rows(
        dataset_source.snapshot_path, f"{language_code}-qrels/*.parquet", cache_dir
    )
    return _build_real_manifest(
        dataset_id=dataset_id,
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=qrel_rows,
        corpus_id_keys=("_id",),
        query_id_keys=("_id",),
        query_text_keys=("text",),
        qrel_query_keys=("query-id",),
        qrel_doc_keys=("corpus-id",),
        qrel_score_keys=("score",),
        corpus_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, f"{language_code}-corpus/*.parquet"
        ),
        query_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, f"{language_code}-queries/*.parquet"
        ),
        judgment_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, f"{language_code}-qrels/*.parquet"
        ),
    )


def load_ms_marco_passage_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MS MARCO Passage benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset("ms_marco_passage", data_root=data_root)
    dataset_source = _require_source(fetched, "corpus_queries")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v1.1/*_passage*.parquet", cache_dir
    )
    query_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v1.1/*_queries*.parquet", cache_dir
    )
    return _build_real_manifest(
        dataset_id="ms_marco_passage",
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=[],
        corpus_id_keys=("docid", "_id"),
        query_id_keys=("qid", "_id"),
        query_text_keys=("query", "text"),
        qrel_query_keys=("qid",),
        qrel_doc_keys=("docid",),
        qrel_score_keys=("relevance", "score"),
        corpus_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v1.1/*_passage*.parquet"
        ),
        query_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v1.1/*_queries*.parquet"
        ),
        judgment_asset_path=dataset_source.snapshot_path,
    )


def load_trec_dl_2019_passage_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real TREC DL 2019 Passage benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset("trec_dl_2019_passage", data_root=data_root)
    dataset_source = _require_source(fetched, "corpus_queries")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v2.1/*_passage*.parquet", cache_dir
    )
    query_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v2.1/*_queries*.parquet", cache_dir
    )
    return _build_real_manifest(
        dataset_id="trec_dl_2019_passage",
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=[],
        corpus_id_keys=("docid", "_id"),
        query_id_keys=("qid", "_id"),
        query_text_keys=("query", "text"),
        qrel_query_keys=("qid",),
        qrel_doc_keys=("docid",),
        qrel_score_keys=("relevance", "score"),
        corpus_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v2.1/*_passage*.parquet"
        ),
        query_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v2.1/*_queries*.parquet"
        ),
        judgment_asset_path=dataset_source.snapshot_path,
    )


def load_trec_dl_2020_passage_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real TREC DL 2020 Passage benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset("trec_dl_2020_passage", data_root=data_root)
    dataset_source = _require_source(fetched, "corpus_queries")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v2.1/*_passage*.parquet", cache_dir
    )
    query_rows = _load_parquet_rows(
        dataset_source.snapshot_path, "v2.1/*_queries*.parquet", cache_dir
    )
    return _build_real_manifest(
        dataset_id="trec_dl_2020_passage",
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=[],
        corpus_id_keys=("docid", "_id"),
        query_id_keys=("qid", "_id"),
        query_text_keys=("query", "text"),
        qrel_query_keys=("qid",),
        qrel_doc_keys=("docid",),
        qrel_score_keys=("relevance", "score"),
        corpus_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v2.1/*_passage*.parquet"
        ),
        query_asset_path=_asset_path_from_pattern(
            dataset_source.snapshot_path, "v2.1/*_queries*.parquet"
        ),
        judgment_asset_path=dataset_source.snapshot_path,
    )


def load_miracl_ko_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MIRACL Korean benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset("miracl_ko", data_root=data_root)
    dataset_source = _require_source(fetched, "dataset")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(dataset_source.snapshot_path, "ko-corpus/*.parquet", cache_dir)
    query_rows = _load_parquet_rows(dataset_source.snapshot_path, "ko-queries/*.parquet", cache_dir)
    qrel_rows = _load_parquet_rows(dataset_source.snapshot_path, "ko-qrels/*.parquet", cache_dir)
    return _build_real_manifest(
        dataset_id="miracl_ko",
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=qrel_rows,
        corpus_id_keys=("_id",),
        query_id_keys=("_id",),
        query_text_keys=("text",),
        qrel_query_keys=("query-id",),
        qrel_doc_keys=("corpus-id",),
        qrel_score_keys=("score",),
        corpus_asset_path=_asset_path_from_pattern(dataset_source.snapshot_path, "ko-corpus/*.parquet"),
        query_asset_path=_asset_path_from_pattern(dataset_source.snapshot_path, "ko-queries/*.parquet"),
        judgment_asset_path=_asset_path_from_pattern(dataset_source.snapshot_path, "ko-qrels/*.parquet"),
    )


def load_mr_tydi_ko_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real Mr. TyDi Korean benchmark manifest from cached public assets."""

    fetched = resolve_cached_benchmark_dataset("mr_tydi_ko", data_root=data_root)
    query_source = _require_source(fetched, "queries_qrels")
    corpus_source = _require_source(fetched, "corpus")
    topics_path = query_source.snapshot_path / "mrtydi-v1.1-korean/ir-format-data/topics.dev.txt"
    qrels_path = query_source.snapshot_path / "mrtydi-v1.1-korean/ir-format-data/qrels.dev.txt"
    corpus_path = corpus_source.snapshot_path / "mrtydi-v1.1-korean/corpus.jsonl.gz"
    return _build_real_manifest(
        dataset_id="mr_tydi_ko",
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=_iter_jsonl_gz_rows(corpus_path),
        query_rows=list(_iter_topics_rows(topics_path)),
        qrel_rows=list(_iter_trec_qrels_rows(qrels_path)),
        corpus_id_keys=("docid",),
        query_id_keys=("query_id",),
        query_text_keys=("query", "text"),
        qrel_query_keys=("query_id",),
        qrel_doc_keys=("doc_id",),
        qrel_score_keys=("relevance",),
        corpus_asset_path=corpus_path,
        query_asset_path=topics_path,
        judgment_asset_path=qrels_path,
    )


def load_beir_scifact_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real BEIR SciFact benchmark manifest from cached public assets."""

    return _load_beir_cached_manifest(
        "beir_scifact",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_beir_nq_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real BEIR NQ benchmark manifest from cached public assets."""

    return _load_beir_cached_manifest(
        "beir_nq",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_beir_fiqa_2018_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real BEIR FiQA 2018 benchmark manifest from cached public assets."""

    return _load_beir_cached_manifest(
        "beir_fiqa_2018",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_beir_arguana_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real BEIR ArguAna benchmark manifest from cached public assets."""

    return _load_beir_cached_manifest(
        "beir_arguana",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_miracl_en_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MIRACL English benchmark manifest from cached public assets."""

    return _load_miracl_cached_manifest(
        "miracl_en",
        "en",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_miracl_ja_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MIRACL Japanese benchmark manifest from cached public assets."""

    return _load_miracl_cached_manifest(
        "miracl_ja",
        "ja",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_miracl_zh_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real MIRACL Chinese benchmark manifest from cached public assets."""

    return _load_miracl_cached_manifest(
        "miracl_zh",
        "zh",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def load_beir_nfcorpus_cached_manifest(
    size: int | None = None,
    *,
    sample_mode: PublicAnchorSampleMode = "standard",
    data_root: Path | None = None,
) -> BenchmarkCorpusManifest:
    """Build a real BEIR NFCorpus benchmark manifest from cached public assets."""

    return _load_beir_cached_manifest(
        "beir_nfcorpus",
        size=size,
        sample_mode=sample_mode,
        data_root=data_root,
    )


def _load_beir_cached_manifest(
    dataset_id: BenchmarkDatasetId,
    *,
    size: int | None,
    sample_mode: PublicAnchorSampleMode,
    data_root: Path | None,
) -> BenchmarkCorpusManifest:
    fetched = resolve_cached_benchmark_dataset(dataset_id, data_root=data_root)
    corpus_queries_source = _require_source(fetched, "corpus_queries")
    qrels_source = _require_source(fetched, "qrels")
    cache_dir = get_benchmark_materialized_root(data_root)
    corpus_rows = _load_parquet_rows(
        corpus_queries_source.snapshot_path,
        "corpus/*.parquet",
        cache_dir,
    )
    query_rows = _load_parquet_rows(
        corpus_queries_source.snapshot_path,
        "queries/*.parquet",
        cache_dir,
    )
    qrels_path = qrels_source.snapshot_path / "test.tsv"
    return _build_real_manifest(
        dataset_id=dataset_id,
        size=size,
        sample_mode=sample_mode,
        fetched=fetched,
        corpus_rows=corpus_rows,
        query_rows=query_rows,
        qrel_rows=list(_iter_headered_tsv_rows(qrels_path)),
        corpus_id_keys=("_id",),
        query_id_keys=("_id",),
        query_text_keys=("text",),
        qrel_query_keys=("query-id",),
        qrel_doc_keys=("corpus-id",),
        qrel_score_keys=("score",),
        corpus_asset_path=_asset_path_from_pattern(
            corpus_queries_source.snapshot_path,
            "corpus/*.parquet",
        ),
        query_asset_path=_asset_path_from_pattern(
            corpus_queries_source.snapshot_path,
            "queries/*.parquet",
        ),
        judgment_asset_path=qrels_path,
    )


def _build_real_manifest(
    *,
    dataset_id: BenchmarkDatasetId,
    size: int | None = None,
    sample_mode: PublicAnchorSampleMode = "standard",
    fetched: BenchmarkDatasetFetchResult,
    corpus_rows: Iterable[Mapping[str, object]],
    query_rows: Iterable[Mapping[str, object]],
    qrel_rows: Iterable[Mapping[str, object]],
    corpus_id_keys: tuple[str, ...],
    query_id_keys: tuple[str, ...],
    query_text_keys: tuple[str, ...],
    qrel_query_keys: tuple[str, ...],
    qrel_doc_keys: tuple[str, ...],
    qrel_score_keys: tuple[str, ...],
    corpus_asset_path: Path,
    query_asset_path: Path,
    judgment_asset_path: Path,
) -> BenchmarkCorpusManifest:
    spec = get_benchmark_dataset_spec(dataset_id)
    metadata = _PUBLIC_DATASET_METADATA[dataset_id]
    query_lookup: dict[str, dict[str, object]] = {}
    query_order: list[str] = []
    for row in query_rows:
        query_id = _require_string_field(row, query_id_keys)
        if query_id in query_lookup:
            continue
        query_text = _require_string_field(row, query_text_keys)
        query_lookup[query_id] = {"id": query_id, "text": query_text}
        query_order.append(query_id)

    judgments_by_query: dict[str, list[dict[str, object]]] = {}
    for row in qrel_rows:
        query_id = _require_string_field(row, qrel_query_keys)
        doc_id = _require_string_field(row, qrel_doc_keys)
        relevance = _require_int_field(row, qrel_score_keys)
        if query_id not in query_lookup:
            continue
        judgments_by_query.setdefault(query_id, []).append(
            {
                "query_id": query_id,
                "doc_id": doc_id,
                "relevance": relevance,
            }
        )

    qrels_backed_query_ids = [
        query_id for query_id in query_order if query_id in judgments_by_query
    ]
    queries_available = len(qrels_backed_query_ids)
    sample_size = resolve_public_anchor_sample_count(
        query_count=queries_available,
        mode=sample_mode,
        explicit_size=size,
    )
    selected_query_ids = qrels_backed_query_ids[:sample_size]
    if not selected_query_ids:
        raise ValueError(f"no qrels-backed queries found for benchmark dataset '{dataset_id}'")

    resolved_sample_mode = "custom" if size is not None else sample_mode
    sampling_strategy = (
        "explicit_query_count_override"
        if size is not None
        else "deterministic_qrels_bounded_mode"
    )

    needed_doc_ids = {
        str(entry["doc_id"])
        for query_id in selected_query_ids
        for entry in judgments_by_query[query_id]
    }
    selected_docs = _select_documents(corpus_rows, needed_doc_ids, corpus_id_keys)
    missing_doc_ids = sorted(needed_doc_ids.difference(selected_docs))
    if missing_doc_ids:
        raise ValueError(
            f"benchmark dataset '{dataset_id}' is missing corpus rows for doc ids: {missing_doc_ids[:5]}"
        )

    documents = [
        _build_document_record(
            dataset_name=metadata["name"],
            language=spec.language,
            row=selected_docs[doc_id],
            doc_id=doc_id,
            index=index,
        )
        for index, doc_id in enumerate(sorted(needed_doc_ids), start=1)
    ]
    queries = [
        _build_query_record(
            dataset_id=dataset_id,
            language=spec.language,
            query_id=query_id,
            text=str(query_lookup[query_id]["text"]),
            index=index,
        )
        for index, query_id in enumerate(selected_query_ids, start=1)
    ]
    judgments = {query_id: judgments_by_query[query_id] for query_id in selected_query_ids}
    provenance = _public_anchor_provenance(
        dataset_id=dataset_id,
        language=spec.language,
        license_name=spec.license,
    )

    return BenchmarkCorpusManifest(
        tier="public_anchor",
        documents=documents,
        queries=queries,
        judgments=judgments,
        dataset_id=dataset_id,
        dataset_name=metadata["name"],
        dataset_description=metadata["description"],
        dataset_metadata={
            "citation": spec.citation,
            "description": metadata["description"],
            "language": spec.language,
            "license": spec.license,
            "queries_available": queries_available,
            "real_public_assets": True,
            "sample_size": len(selected_query_ids),
            "sample_mode": resolved_sample_mode,
            "sampling_strategy": sampling_strategy,
            "source_url": spec.source_url,
            "sources": [
                {
                    "label": source.label,
                    "name": source.name,
                    "repo_id": source.repo_id,
                    "requested_revision": source.requested_revision,
                    "allow_patterns": list(source.allow_patterns),
                    "resolved_snapshot_path": source.snapshot_path.as_posix(),
                }
                for source in fetched.sources
            ],
            "synthetic_sample": False,
        },
        corpus_assets=(
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_real_corpus",
                path=corpus_asset_path.as_posix(),
                provenance=provenance,
            ),
        ),
        query_assets=(
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_real_queries",
                path=query_asset_path.as_posix(),
                provenance=provenance,
            ),
        ),
        judgment_assets=(
            BenchmarkAssetManifest(
                asset_id=f"{dataset_id}_real_qrels",
                path=judgment_asset_path.as_posix(),
                provenance=provenance,
            ),
        ),
    )


def _public_anchor_provenance(
    *, dataset_id: str, language: str, license_name: str
) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        source_class="public_dataset",
        authoring_method="automated",
        license=license_name,
        collection_method="cached_public_dataset_manifest_sampling",
        visibility_tier="public",
        contamination_status="clean",
        family_dedupe_key=f"public-anchor:{dataset_id}:{language}",
        authority_tier="public_anchor",
    )


def _build_document_record(
    *,
    dataset_name: str,
    language: str,
    row: Mapping[str, object],
    doc_id: str,
    index: int,
) -> dict[str, object]:
    raw_title = _optional_string_field(row, ("title",)) or doc_id
    raw_text = _optional_string_field(row, ("text", "content", "contents"))
    if not raw_text:
        raise ValueError(f"benchmark corpus row '{doc_id}' is missing text content")
    title = _normalize_imported_title(raw_title, fallback=doc_id)
    text = _normalize_imported_public_text(raw_text)
    content = text if not title or title == doc_id else f"{title}\n\n{text}"
    return {
        "id": doc_id,
        "content": content,
        "metadata": {
            "title": title,
            "summary": _summarize_text(text),
            "recorded_at": _recorded_at(index),
            "language": language,
            "source_dataset": dataset_name,
            "source_id": doc_id,
        },
    }


def _build_query_record(
    *,
    dataset_id: str,
    language: str,
    query_id: str,
    text: str,
    index: int,
) -> dict[str, object]:
    query_kind = "known-item" if index % 2 else "topical"
    return {
        "id": query_id,
        "text": text,
        "group": language,
        "kind": query_kind,
        "tags": [language, "public_anchor", dataset_id, "real_public_asset"],
    }


def _summarize_text(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= 160:
        return normalized
    return f"{normalized[:157]}..."


def _recorded_at(index: int) -> str:
    base = datetime(2026, 3, 1, tzinfo=UTC)
    return (base + timedelta(days=index - 1)).isoformat().replace("+00:00", "Z")


def _normalize_imported_title(title: str, *, fallback: str) -> str:
    normalized = _normalize_imported_public_text(title)
    if len(normalized) <= _MAX_IMPORTED_TITLE_LENGTH:
        return normalized
    bounded = normalized[: _MAX_IMPORTED_TITLE_LENGTH - 1].rstrip(" ,.;:-")
    bounded = bounded or fallback
    return f"{bounded}…"


def _normalize_imported_public_text(text: str) -> str:
    normalized = text
    previous = None
    while previous != normalized:
        previous = normalized
        normalized = _WIKILINK_PATTERN.sub(_replace_wikilink_markup, normalized)
        normalized = _TEMPLATE_PATTERN.sub(_replace_template_markup, normalized)
    normalized = normalized.replace("[[", "(").replace("]]", ")")
    normalized = normalized.replace("{{", "(").replace("}}", ")")
    normalized = re.sub(r"\[(?:File|Image|Category|Media):[^\]]+\]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _replace_wikilink_markup(match: re.Match[str]) -> str:
    raw_value = match.group(1).strip()
    if not raw_value:
        return ""
    parts = [part.strip() for part in raw_value.split("|") if part.strip()]
    if not parts:
        return ""
    first_part = parts[0].casefold()
    if first_part.startswith(_MEDIA_NAMESPACE_PREFIXES):
        return ""
    for candidate in reversed(parts):
        if candidate:
            return candidate
    return ""


def _replace_template_markup(match: re.Match[str]) -> str:
    raw_value = match.group(1).strip()
    if not raw_value:
        return ""
    parts = [part.strip() for part in raw_value.split("|") if part.strip()]
    if len(parts) <= 1:
        return ""
    for candidate in reversed(parts[1:]):
        if "=" not in candidate and candidate:
            return candidate
    return ""


def _load_parquet_rows(
    snapshot_path: Path, pattern: str, cache_dir: Path
) -> list[dict[str, object]]:
    files = sorted(snapshot_path.glob(pattern))
    if not files:
        raise ValueError(
            f"expected cached parquet files matching '{pattern}' under {snapshot_path.as_posix()}"
        )
    datasets_module = import_module("datasets")
    load_dataset = cast(Callable[..., object], datasets_module.load_dataset)
    dataset = load_dataset(
        "parquet",
        data_files=[file.as_posix() for file in files],
        split="train",
        cache_dir=cache_dir.as_posix(),
    )
    return [cast(dict[str, object], row) for row in cast(Iterable[object], dataset)]


def _select_documents(
    corpus_rows: Iterable[Mapping[str, object]],
    needed_doc_ids: set[str],
    id_keys: tuple[str, ...],
) -> dict[str, Mapping[str, object]]:
    documents: dict[str, Mapping[str, object]] = {}
    for row in corpus_rows:
        doc_id = _optional_string_field(row, id_keys)
        if doc_id is None or doc_id not in needed_doc_ids or doc_id in documents:
            continue
        documents[doc_id] = row
        if len(documents) == len(needed_doc_ids):
            break
    return documents


def _require_source(
    fetched: BenchmarkDatasetFetchResult, label: str
) -> BenchmarkDatasetSourceFetch:
    for source in fetched.sources:
        if source.label == label:
            return source
    raise ValueError(f"benchmark dataset '{fetched.dataset_id}' is missing source '{label}'")


def _asset_path_from_pattern(snapshot_path: Path, pattern: str) -> Path:
    files = sorted(snapshot_path.glob(pattern))
    if not files:
        raise ValueError(
            f"expected cached asset files matching '{pattern}' under {snapshot_path.as_posix()}"
        )
    if len(files) == 1:
        return files[0]
    return files[0].parent


def _iter_jsonl_gz_rows(path: Path) -> Iterable[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"expected JSON object rows in {path.as_posix()}")
            yield {str(key): value for key, value in payload.items()}


def _iter_topics_rows(path: Path) -> Iterable[dict[str, object]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        query_id, query_text = line.split("\t", maxsplit=1)
        yield {"query_id": query_id, "query": query_text}


def _iter_trec_qrels_rows(path: Path) -> Iterable[dict[str, object]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        query_id, _placeholder, doc_id, relevance = line.split()
        yield {
            "query_id": query_id,
            "doc_id": doc_id,
            "relevance": int(relevance),
        }


def _iter_headered_tsv_rows(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        for row in reader:
            yield {str(key): value for key, value in row.items() if key is not None}


def _require_string_field(row: Mapping[str, object], keys: tuple[str, ...]) -> str:
    value = _optional_string_field(row, keys)
    if value is None:
        raise ValueError(f"row is missing required string field from keys {keys}")
    return value


def _optional_string_field(
    row: Mapping[str, object], keys: tuple[str, ...]
) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _require_int_field(row: Mapping[str, object], keys: tuple[str, ...]) -> int:
    for key in keys:
        value = row.get(key)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(value)
    raise ValueError(f"row is missing required integer field from keys {keys}")


__all__ = [
    "FULL_CAP",
    "PublicAnchorSampleMode",
    "QUICK_SIZE",
    "STANDARD_SIZE",
    "load_beir_arguana_cached_manifest",
    "load_beir_fiqa_2018_cached_manifest",
    "load_beir_nfcorpus_cached_manifest",
    "load_beir_nq_cached_manifest",
    "load_beir_scifact_cached_manifest",
    "load_miracl_en_cached_manifest",
    "load_miracl_ja_cached_manifest",
    "load_miracl_ko_cached_manifest",
    "load_miracl_zh_cached_manifest",
    "load_mr_tydi_ko_cached_manifest",
    "load_ms_marco_passage_cached_manifest",
    "load_trec_dl_2019_passage_cached_manifest",
    "load_trec_dl_2020_passage_cached_manifest",
    "resolve_public_anchor_sample_count",
]
