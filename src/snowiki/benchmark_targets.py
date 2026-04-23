from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

from snowiki.bench.datasets import (
    missing_materialized_asset_message,
    resolve_dataset_assets,
)
from snowiki.bench.specs import (
    BenchmarkQuery,
    DatasetManifest,
    LevelConfig,
    QueryResult,
)
from snowiki.search.bm25_index import BM25SearchDocument, BM25SearchIndex
from snowiki.search.indexer import InvertedIndex, SearchDocument
from snowiki.search.registry import create, default

BENCHMARK_RETRIEVAL_LIMIT = 100


class _LexicalRegexTargetAdapter:
    """Benchmark target adapter for lexical retrieval with the regex tokenizer."""

    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, object]:
        del level
        documents = tuple(
            SearchDocument(
                id=doc_id,
                path=doc_id,
                title=doc_id,
                kind="benchmark_doc",
                content=text,
            )
            for doc_id, text in _load_materialized_corpus_rows(manifest)
        )
        index = InvertedIndex(documents, tokenizer=create(default().name))
        results = tuple(
            _run_lexical_query(index=index, query=query) for query in queries
        )
        return {"results": results}


class _BM25TargetAdapter:
    """Benchmark target adapter for BM25 retrieval with a canonical tokenizer."""

    _tokenizer_name: str

    def __init__(self, tokenizer_name: str) -> None:
        self._tokenizer_name = tokenizer_name

    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, object]:
        del level
        documents = tuple(
            BM25SearchDocument(
                id=doc_id,
                path=doc_id,
                title=doc_id,
                kind="benchmark_doc",
                content=text,
            )
            for doc_id, text in _load_materialized_corpus_rows(manifest)
        )
        index = BM25SearchIndex(documents, tokenizer_name=self._tokenizer_name)
        results = tuple(_run_bm25_query(index=index, query=query) for query in queries)
        return {"results": results}


def _load_materialized_corpus_rows(
    manifest: DatasetManifest,
) -> tuple[tuple[str, str], ...]:
    corpus_path = resolve_dataset_assets(manifest)["corpus"]
    if not corpus_path.is_file():
        raise FileNotFoundError(
            missing_materialized_asset_message(
                manifest,
                asset_name="corpus",
                path=corpus_path,
            )
        )

    from datasets import load_dataset

    dataset = cast(
        Iterable[object],
        load_dataset("parquet", data_files=str(corpus_path), split="train"),
    )
    rows: list[tuple[str, str]] = []
    for row in dataset:
        if not isinstance(row, Mapping):
            raise ValueError(f"Expected corpus row mappings in {corpus_path}")
        typed_row = cast(Mapping[str, object], row)
        rows.append(
            (
                _require_corpus_field(
                    typed_row,
                    key="docid",
                    corpus_path=corpus_path,
                ),
                _require_corpus_field(
                    typed_row,
                    key="text",
                    corpus_path=corpus_path,
                ),
            )
        )
    return tuple(rows)


def _require_corpus_field(
    row: Mapping[str, object],
    *,
    key: str,
    corpus_path: Path,
) -> str:
    value = row.get(key)
    if value in (None, ""):
        raise ValueError(f"Missing corpus field {key!r} in {corpus_path}")
    return str(value)


def _run_lexical_query(
    *,
    index: InvertedIndex,
    query: BenchmarkQuery,
) -> QueryResult:
    start = time.perf_counter()
    hits = index.search(query.query_text, limit=BENCHMARK_RETRIEVAL_LIMIT)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return QueryResult(
        query_id=query.query_id,
        ranked_doc_ids=tuple(hit.document.id for hit in hits),
        latency_ms=latency_ms,
    )


def _run_bm25_query(
    *,
    index: BM25SearchIndex,
    query: BenchmarkQuery,
) -> QueryResult:
    start = time.perf_counter()
    hits = index.search(query.query_text, limit=BENCHMARK_RETRIEVAL_LIMIT)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return QueryResult(
        query_id=query.query_id,
        ranked_doc_ids=tuple(hit.document.id for hit in hits),
        latency_ms=latency_ms,
    )


LEXICAL_REGEX_TARGET_ADAPTER = _LexicalRegexTargetAdapter()
BM25_REGEX_TARGET_ADAPTER = _BM25TargetAdapter("regex_v1")
BM25_KIWI_MORPHOLOGY_TARGET_ADAPTER = _BM25TargetAdapter("kiwi_morphology_v1")
BM25_KIWI_NOUNS_TARGET_ADAPTER = _BM25TargetAdapter("kiwi_nouns_v1")
BM25_MECAB_MORPHOLOGY_TARGET_ADAPTER = _BM25TargetAdapter("mecab_morphology_v1")
BM25_HF_WORDPIECE_TARGET_ADAPTER = _BM25TargetAdapter("hf_wordpiece_v1")
