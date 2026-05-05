from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from snowiki.compiler.engine import CompilerEngine
from snowiki.schema.compiled import CompiledPage
from snowiki.schema.normalized import NormalizedRecord

from .corpus import runtime_corpus_from_records_and_pages
from .engine import BM25RuntimeIndex
from .protocols import RuntimeSearchIndex
from .registry import SearchTokenizer, default
from .registry import create as create_tokenizer


@dataclass(frozen=True, slots=True)
class RetrievalSnapshot:
    index: RuntimeSearchIndex
    records_indexed: int
    pages_indexed: int


class RetrievalService:
    """Canonical retrieval assembly service."""

    @classmethod
    def from_root(
        cls,
        root: Path,
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot:
        compiler = CompilerEngine(root)
        records = compiler.load_normalized_records()
        pages = compiler.build_pages(records) if records else []
        return cls.from_records_and_pages(
            records=records,
            pages=pages,
            tokenizer=tokenizer,
        )

    @classmethod
    def from_records_and_pages(
        cls,
        *,
        records: list[NormalizedRecord],
        pages: list[CompiledPage],
        tokenizer: SearchTokenizer | None = None,
    ) -> RetrievalSnapshot:
        if records and not all(isinstance(r, NormalizedRecord) for r in records):
            raise TypeError(
                "records must be typed NormalizedRecord instances, not dict/mappings"
            )
        if pages and not all(isinstance(p, CompiledPage) for p in pages):
            raise TypeError(
                "pages must be typed CompiledPage instances, not dict/mappings"
            )
        resolved_tokenizer = tokenizer or create_tokenizer(default().name)
        runtime_tokenizer_name = getattr(resolved_tokenizer, "name", default().name)
        if not isinstance(runtime_tokenizer_name, str):
            runtime_tokenizer_name = default().name
        corpus = runtime_corpus_from_records_and_pages(
            records=records,
            pages=pages,
        )
        return RetrievalSnapshot(
            index=BM25RuntimeIndex(
                corpus,
                tokenizer_name=runtime_tokenizer_name,
                tokenizer=resolved_tokenizer,
            ),
            records_indexed=len(records),
            pages_indexed=len(pages),
        )
