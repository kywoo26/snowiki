from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from snowiki.compiler.engine import CompilerEngine
from snowiki.config import resolve_repo_asset_path
from snowiki.search import (
    BM25SearchDocument,
    BM25SearchHit,
    BM25SearchIndex,
    build_lexical_index,
)
from snowiki.search.indexer import InvertedIndex, SearchDocument, SearchHit
from snowiki.search.registry import resolve_legacy_tokenizer
from snowiki.search.workspace import (
    RetrievalService,
    compiled_page_to_search_mapping,
    load_normalized_records,
)

from ..contract.presets import normalize_benchmark_baseline
from ..reporting.models import (
    PAGE_LIST_ADAPTER,
    RECORD_LIST_ADAPTER,
    PageModel,
    RecordModel,
)
from ..runtime.corpus import CANONICAL_BENCHMARK_FIXTURE_PATHS


@dataclass(frozen=True)
class CorpusBundle:
    records: tuple[RecordModel, ...]
    pages: tuple[PageModel, ...]
    raw_index: InvertedIndex
    blended_index: InvertedIndex


def build_corpus(root: Path) -> CorpusBundle:
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


def run_lexical(index: InvertedIndex, query: str, top_k: int) -> list[SearchHit]:
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


def bm25_hit_to_search_hit(hit: BM25SearchHit) -> SearchHit:
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


def build_bm25_index(
    documents: tuple[SearchDocument, ...], *, tokenizer_name: str
) -> BM25SearchIndex:
    return BM25SearchIndex(
        [_bm25_document_from_search(document) for document in documents],
        tokenizer_name=tokenizer_name,
    )


def tokenizer_name_for_baseline(baseline: str) -> str:
    normalized_baseline = normalize_benchmark_baseline(baseline)
    if normalized_baseline == "bm25s":
        resolved = resolve_legacy_tokenizer(use_kiwi_tokenizer=False)
        if resolved is None:
            raise ValueError(f"could not resolve tokenizer for baseline: {baseline}")
        return resolved

    if normalized_baseline.startswith("bm25s_"):
        resolved = resolve_legacy_tokenizer(benchmark_alias=normalized_baseline)
        if resolved is None:
            raise ValueError(f"unsupported baseline: {baseline}")
        return resolved

    raise ValueError(f"unsupported baseline: {baseline}")


def _benchmark_fixture_sources() -> dict[str, str]:
    return {
        resolve_repo_asset_path(relative_path).resolve().as_posix(): fixture_id
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    }


def _benchmark_fixture_digests() -> dict[str, str]:
    return {
        hashlib.sha256(resolve_repo_asset_path(relative_path).read_bytes()).hexdigest(): fixture_id
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


def benchmark_hit_lookup(corpus: CorpusBundle) -> dict[str, str]:
    record_lookup = _record_fixture_lookup(corpus.records)
    return {**record_lookup, **_page_fixture_lookup(corpus.pages, record_lookup)}


__all__ = [
    "CorpusBundle",
    "benchmark_hit_lookup",
    "bm25_hit_to_search_hit",
    "build_bm25_index",
    "build_corpus",
    "run_lexical",
    "tokenizer_name_for_baseline",
]
