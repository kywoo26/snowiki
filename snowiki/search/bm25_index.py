from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import bm25s
import numpy as np

from .kiwi_tokenizer import KoreanTokenizer

if TYPE_CHECKING:
    from datetime import datetime
    from collections.abc import Iterable, Sequence


@dataclass(frozen=True)
class BM25SearchDocument:
    id: str
    path: str
    kind: str
    title: str
    content: str
    summary: str = ""
    aliases: tuple[str, ...] = ()
    recorded_at: datetime | None = None
    source_type: str = ""


@dataclass(frozen=True)
class BM25SearchHit:
    document: BM25SearchDocument
    score: float
    matched_terms: tuple[str, ...]


class BM25SearchIndex:
    """BM25 search index using bm25s library with Kiwi tokenization.

    This index supports multiple BM25 variants:
    - "robertson": Robertson et al. (standard Okapi BM25)
    - "atire": ATIRE variant
    - "bm25l": BM25L (length-normalized)
    - "bm25+": BM25+ (improved version)
    - "lucene": Lucene variant

    Args:
        documents: Iterable of documents to index
        method: BM25 variant to use (default: "lucene")
        k1: Term frequency saturation parameter (default: 1.5)
        b: Document length normalization (default: 0.75)
        delta: BM25+ delta parameter (default: 0.5)
    """

    BM25_METHODS = frozenset(["robertson", "atire", "bm25l", "bm25+", "lucene"])

    def __init__(
        self,
        documents: Iterable[BM25SearchDocument],
        method: str = "lucene",
        k1: float = 1.5,
        b: float = 0.75,
        delta: float = 0.5,
    ) -> None:
        if method not in self.BM25_METHODS:
            raise ValueError(
                f"Invalid method: {method}. Must be one of {self.BM25_METHODS}"
            )

        self.documents = list(documents)
        self.method = method
        self.k1 = k1
        self.b = b
        self.delta = delta

        self.tokenizer = KoreanTokenizer()
        self._build_index()

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        if not self.documents:
            self.corpus_tokens = []
            self.bm25 = bm25s.BM25(method=self.method)
            return

        corpus = []
        for doc in self.documents:
            text = f"{doc.title}\n{doc.content}\n{doc.summary}"
            corpus.append(text)

        corpus_tokens = bm25s.tokenize(
            corpus,
            stopwords="en",
            return_ids=False,
        )

        for i, tokens in enumerate(corpus_tokens):
            korean_tokens = self.tokenizer(corpus[i])
            tokens.extend(korean_tokens)

        self.corpus_tokens = corpus_tokens
        self.bm25 = bm25s.BM25(method=self.method, k1=self.k1, b=self.b)
        self.bm25.index(corpus_tokens)

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[BM25SearchHit]:
        """Search documents using BM25 scoring."""
        if not self.documents:
            return []

        tokenized = bm25s.tokenize(query, stopwords="en", return_ids=False)
        query_tokens_nested = [list(tokenized[0])]
        query_tokens_nested[0].extend(self.tokenizer(query))

        if not query_tokens_nested[0]:
            return []

        results = self.bm25.retrieve(
            query_tokens_nested,
            k=min(limit, len(self.documents)),
        )

        hits = []
        doc_indices = results[0].flatten()
        scores = results[1].flatten()
        for i in range(len(doc_indices)):
            doc_idx = int(doc_indices[i])
            score = float(scores[i])
            doc = self.documents[doc_idx]
            hits.append(
                BM25SearchHit(
                    document=doc,
                    score=score,
                    matched_terms=tuple(query_tokens_nested[0]),
                )
            )

        return hits

    def save(self, path: str) -> None:
        """Save index to disk."""
        self.bm25.save(path)

    @classmethod
    def load(
        cls, path: str, documents: Iterable[BM25SearchDocument]
    ) -> BM25SearchIndex:
        """Load index from disk."""
        instance = cls.__new__(cls)
        instance.documents = list(documents)
        instance.tokenizer = KoreanTokenizer()
        instance.bm25 = bm25s.BM25.load(path, load_corpus=True)
        return instance
