from __future__ import annotations

import hashlib
import random
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

from snowiki.bench.cache import (
    build_bm25_cache_identity,
    load_or_rebuild_bm25_cache,
)
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
from snowiki.config import get_snowiki_root
from snowiki.search.bm25_index import BM25SearchDocument, BM25SearchIndex
from snowiki.search.indexer import InvertedIndex, SearchDocument
from snowiki.search.registry import create, default
from snowiki.search.registry import get as get_tokenizer_spec
from snowiki.storage.zones import StoragePaths

BENCHMARK_RETRIEVAL_LIMIT = 100
CORPUS_SAMPLING_SEED = 2718


class _LexicalRegexTargetAdapter:
    """Benchmark target adapter for lexical retrieval with the regex tokenizer."""

    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, object]:
        documents = tuple(
            SearchDocument(
                id=doc_id,
                path=doc_id,
                title=doc_id,
                kind="benchmark_doc",
                content=text,
            )
            for doc_id, text in _load_materialized_corpus_rows(
                manifest,
                level=level,
            )
        )
        index = InvertedIndex(documents, tokenizer=create(default().name))
        results = tuple(
            _run_lexical_query(index=index, query=query) for query in queries
        )
        return {"results": results}


class _BM25TargetAdapter:
    """Benchmark target adapter for BM25 retrieval with a canonical tokenizer."""

    _target_name: str
    _tokenizer_name: str

    def __init__(self, target_name: str, tokenizer_name: str) -> None:
        self._target_name = target_name
        self._tokenizer_name = tokenizer_name

    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, object]:
        corpus_rows = _load_materialized_corpus_rows(
            manifest,
            level=level,
        )
        documents = tuple(
            BM25SearchDocument(
                id=doc_id,
                path=doc_id,
                title=doc_id,
                kind="benchmark_doc",
                content=text,
            )
            for doc_id, text in corpus_rows
        )
        identity = self._cache_identity(
            manifest=manifest,
            level=level,
            corpus_rows=corpus_rows,
        )

        def _build_artifact() -> tuple[BM25SearchIndex, bytes]:
            index = BM25SearchIndex(documents, tokenizer_name=self._tokenizer_name)
            return index, index.to_cache_bytes()

        def _load_artifact(path: Path) -> BM25SearchIndex:
            return BM25SearchIndex.load_cache_artifact(
                path,
                documents,
                expected_tokenizer_name=self._tokenizer_name,
            )

        cache_result = load_or_rebuild_bm25_cache(
            storage_paths=StoragePaths(get_snowiki_root()),
            identity=identity,
            build_artifact=_build_artifact,
            load_artifact=_load_artifact,
        )
        index = cache_result.value
        results = tuple(_run_bm25_query(index=index, query=query) for query in queries)
        return {"results": results, "cache": cache_result.metadata}

    def _cache_identity(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        corpus_rows: tuple[tuple[str, str], ...],
    ) -> dict[str, object]:
        tokenizer_spec = get_tokenizer_spec(self._tokenizer_name)
        corpus_path = resolve_dataset_assets(manifest, level_id=level.level_id)["corpus"]
        return build_bm25_cache_identity(
            target_name=self._target_name,
            corpus_identity=corpus_path.as_posix(),
            corpus_hash=_sha256_file(corpus_path),
            corpus_cap=level.corpus_cap,
            documents=corpus_rows,
            tokenizer_name=tokenizer_spec.name,
            tokenizer_config={
                "family": tokenizer_spec.family,
                "runtime_supported": tokenizer_spec.runtime_supported,
            },
            tokenizer_version=tokenizer_spec.version,
            bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
        )


def _load_materialized_corpus_rows(
    manifest: DatasetManifest,
    *,
    level: LevelConfig,
) -> tuple[tuple[str, str], ...]:
    corpus_path = resolve_dataset_assets(manifest, level_id=level.level_id)["corpus"]
    if not corpus_path.is_file():
        raise FileNotFoundError(
            missing_materialized_asset_message(
                manifest,
                asset_name="corpus",
                path=corpus_path,
                level_id=level.level_id,
            )
        )

    from datasets import load_dataset

    dataset = cast(
        Iterable[object],
        load_dataset("parquet", data_files=str(corpus_path), split="train"),
    )
    if level.corpus_cap is None:
        rows: list[tuple[str, str]] = []
        for row in dataset:
            rows.append(_coerce_corpus_row(row, corpus_path=corpus_path))
        return tuple(rows)

    corpus_cap = level.corpus_cap
    judged_doc_ids = _load_judged_doc_ids(manifest, level_id=level.level_id)
    fill_size = max(corpus_cap, len(judged_doc_ids)) - len(judged_doc_ids)
    buffered_rows: list[tuple[str, str]] = []
    judged_rows: dict[str, tuple[str, str]] = {}
    sampled_rows: list[tuple[str, str]] = []
    non_judged_seen = 0
    sampler = random.Random(CORPUS_SAMPLING_SEED)

    # Keep every judged document in the sample so metric-bearing documents never
    # disappear from quick or standard runs. Then fill the remaining budget with
    # a deterministic random sample to preserve rough corpus realism at lower cost.
    for row in dataset:
        corpus_row = _coerce_corpus_row(row, corpus_path=corpus_path)
        if len(buffered_rows) <= corpus_cap:
            buffered_rows.append(corpus_row)
        doc_id = corpus_row[0]
        if doc_id in judged_doc_ids:
            judged_rows.setdefault(doc_id, corpus_row)
            continue

        if fill_size <= 0:
            continue
        non_judged_seen += 1
        if len(sampled_rows) < fill_size:
            sampled_rows.append(corpus_row)
            continue
        replacement_index = sampler.randrange(non_judged_seen)
        if replacement_index < fill_size:
            sampled_rows[replacement_index] = corpus_row

    # When the corpus already fits under the configured cap, preserve the original
    # row order so small-dataset benchmark behavior remains unchanged.
    if len(buffered_rows) <= corpus_cap:
        return tuple(buffered_rows)

    return tuple(judged_rows.values()) + tuple(sampled_rows)


def _coerce_corpus_row(row: object, *, corpus_path: Path) -> tuple[str, str]:
    if not isinstance(row, Mapping):
        raise ValueError(f"Expected corpus row mappings in {corpus_path}")
    typed_row = cast(Mapping[str, object], row)
    return (
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


def _load_judged_doc_ids(manifest: DatasetManifest, *, level_id: str | None = None) -> set[str]:
    judgments_path = resolve_dataset_assets(manifest, level_id=level_id)["judgments"]
    if not judgments_path.is_file():
        raise FileNotFoundError(
            missing_materialized_asset_message(
                manifest,
                asset_name="judgments",
                path=judgments_path,
                level_id=level_id,
            )
        )

    judged_doc_ids: set[str] = set()
    with judgments_path.open(encoding="utf-8") as judgments_file:
        for line_number, raw_line in enumerate(judgments_file):
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if line_number == 0 and line.startswith("qid\tdocid\t"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise ValueError(f"Malformed judgment row in {judgments_path}: {line!r}")
            judged_doc_ids.add(parts[1])
    return judged_doc_ids


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
BM25_REGEX_TARGET_ADAPTER = _BM25TargetAdapter("bm25_regex_v1", "regex_v1")
BM25_KIWI_MORPHOLOGY_TARGET_ADAPTER = _BM25TargetAdapter(
    "bm25_kiwi_morphology_v1",
    "kiwi_morphology_v1",
)
BM25_KIWI_NOUNS_TARGET_ADAPTER = _BM25TargetAdapter(
    "bm25_kiwi_nouns_v1",
    "kiwi_nouns_v1",
)
BM25_MECAB_MORPHOLOGY_TARGET_ADAPTER = _BM25TargetAdapter(
    "bm25_mecab_morphology_v1",
    "mecab_morphology_v1",
)
BM25_HF_WORDPIECE_TARGET_ADAPTER = _BM25TargetAdapter(
    "bm25_hf_wordpiece_v1",
    "hf_wordpiece_v1",
)
