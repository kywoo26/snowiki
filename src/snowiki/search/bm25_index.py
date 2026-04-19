from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import bm25s

from .kiwi_tokenizer import (
    KIWI_LEXICAL_CANDIDATE_MODES,
    KiwiLexicalCandidateMode,
)
from .registry import SearchTokenizer, create, default, get, resolve_legacy_tokenizer
from .workspace import normalize_stored_tokenizer_name, require_tokenizer_compatibility

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime


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

    BM25_METHODS: frozenset[str] = frozenset(
        ["robertson", "atire", "bm25l", "bm25+", "lucene"]
    )
    DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE: KiwiLexicalCandidateMode = "morphology"
    _METADATA_SUFFIX = ".snowiki_meta.json"
    _SHOW_PROGRESS = False
    _LEAVE_PROGRESS = False
    _TOKENIZER_NAMES: frozenset[str] = frozenset(
        ["regex_v1", "kiwi_morphology_v1", "kiwi_nouns_v1"]
    )

    def __init__(
        self,
        documents: Iterable[BM25SearchDocument],
        method: str = "lucene",
        k1: float = 1.5,
        b: float = 0.75,
        delta: float = 0.5,
        tokenizer_name: str | None = None,
        use_kiwi_tokenizer: bool = True,
        kiwi_lexical_candidate_mode: KiwiLexicalCandidateMode = DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE,
    ) -> None:
        if method not in self.BM25_METHODS:
            raise ValueError(
                f"Invalid method: {method}. Must be one of {self.BM25_METHODS}"
            )
        if kiwi_lexical_candidate_mode not in KIWI_LEXICAL_CANDIDATE_MODES:
            raise ValueError(
                "Invalid Kiwi lexical candidate mode: "
                + f"{kiwi_lexical_candidate_mode}. Must be one of "
                + f"{sorted(KIWI_LEXICAL_CANDIDATE_MODES)}"
            )

        resolved_tokenizer_name = self._resolve_tokenizer_name(
            tokenizer_name=tokenizer_name,
            use_kiwi_tokenizer=use_kiwi_tokenizer,
            kiwi_lexical_candidate_mode=kiwi_lexical_candidate_mode,
        )
        legacy_flags = self._legacy_tokenizer_flags(resolved_tokenizer_name)

        self.documents: list[BM25SearchDocument] = list(documents)
        self.method: str = method
        self.k1: float = k1
        self.b: float = b
        self.delta: float = delta
        self.tokenizer_name: str = resolved_tokenizer_name
        self.use_kiwi_tokenizer = legacy_flags[0]
        self.kiwi_lexical_candidate_mode = legacy_flags[1]

        self.tokenizer: SearchTokenizer | None = (
            create(resolved_tokenizer_name) if self.use_kiwi_tokenizer else None
        )
        self.corpus_tokens: list[list[str]] = []
        self.bm25: Any
        self._build_index()

    @classmethod
    def _metadata_path(cls, path: str) -> Path:
        return Path(f"{path}{cls._METADATA_SUFFIX}")

    def _metadata_payload(self) -> dict[str, object]:
        return {
            "method": self.method,
            "k1": self.k1,
            "b": self.b,
            "delta": self.delta,
            "tokenizer_name": self.tokenizer_name,
            "use_kiwi_tokenizer": self.use_kiwi_tokenizer,
            "kiwi_lexical_candidate_mode": self.kiwi_lexical_candidate_mode,
        }

    @classmethod
    def _resolve_tokenizer_name(
        cls,
        *,
        tokenizer_name: str | None,
        use_kiwi_tokenizer: bool,
        kiwi_lexical_candidate_mode: KiwiLexicalCandidateMode,
    ) -> str:
        resolved = tokenizer_name or resolve_legacy_tokenizer(
            use_kiwi_tokenizer=use_kiwi_tokenizer,
            kiwi_lexical_candidate_mode=kiwi_lexical_candidate_mode,
        )
        if resolved is None:
            resolved = default().name

        spec = get(resolved)
        if resolved not in cls._TOKENIZER_NAMES:
            supported = ", ".join(sorted(cls._TOKENIZER_NAMES))
            raise ValueError(
                f"Invalid BM25 tokenizer: {resolved}. Must be one of {supported}"
            )
        if not spec.benchmark_supported:
            raise ValueError(f"Tokenizer is not benchmark-supported: {resolved}")
        return spec.name

    @classmethod
    def _legacy_tokenizer_flags(
        cls, tokenizer_name: str
    ) -> tuple[bool, KiwiLexicalCandidateMode]:
        if tokenizer_name == "regex_v1":
            return False, cls.DEFAULT_KIWI_LEXICAL_CANDIDATE_MODE
        if tokenizer_name == "kiwi_nouns_v1":
            return True, "nouns"
        return True, "morphology"

    @staticmethod
    def _metadata_float(metadata: dict[str, object], key: str, default: float) -> float:
        value = metadata.get(key, default)
        return float(cast(float | int | str, value))

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        if not self.documents:
            self.corpus_tokens = []
            self.bm25 = bm25s.BM25(method=self.method)
            return

        corpus: list[str] = []
        for doc in self.documents:
            text = f"{doc.title}\n{doc.content}\n{doc.summary}"
            corpus.append(text)

        if self.tokenizer is not None:
            corpus_tokens = [list(self.tokenizer.tokenize(text)) for text in corpus]
        else:
            corpus_tokens = cast(
                list[list[str]],
                bm25s.tokenize(
                    corpus,
                    stopwords="en",
                    return_ids=False,
                    show_progress=self._SHOW_PROGRESS,
                    leave=self._LEAVE_PROGRESS,
                ),
            )

        self.corpus_tokens = corpus_tokens
        self.bm25 = bm25s.BM25(method=self.method, k1=self.k1, b=self.b)
        self.bm25.index(
            corpus_tokens,
            show_progress=self._SHOW_PROGRESS,
            leave_progress=self._LEAVE_PROGRESS,
        )

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[BM25SearchHit]:
        """Search documents using BM25 scoring."""
        if not self.documents:
            return []

        if self.tokenizer is not None:
            query_tokens_nested: list[list[str]] = [list(self.tokenizer.tokenize(query))]
        else:
            tokenized = cast(
                list[list[str]],
                bm25s.tokenize(
                    query,
                    stopwords="en",
                    return_ids=False,
                    show_progress=self._SHOW_PROGRESS,
                    leave=self._LEAVE_PROGRESS,
                ),
            )
            query_tokens_nested = [list(tokenized[0])]

        if not query_tokens_nested[0]:
            return []

        results = self.bm25.retrieve(
            query_tokens_nested,
            k=min(limit, len(self.documents)),
            show_progress=self._SHOW_PROGRESS,
            leave_progress=self._LEAVE_PROGRESS,
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
        _ = self._metadata_path(path).write_text(
            json.dumps(self._metadata_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(
        cls,
        path: str,
        documents: Iterable[BM25SearchDocument],
        *,
        expected_tokenizer_name: str | None = None,
    ) -> BM25SearchIndex:
        """Load index from disk."""
        metadata_path = cls._metadata_path(path)
        metadata: dict[str, object] = {}
        if metadata_path.exists():
            metadata = cast(dict[str, object], json.loads(metadata_path.read_text()))

        requested_tokenizer_name = (
            expected_tokenizer_name
            or normalize_stored_tokenizer_name(metadata)
            or default().name
        )
        tokenizer_name = require_tokenizer_compatibility(
            artifact_path=metadata_path,
            requested_tokenizer_name=requested_tokenizer_name,
            metadata=metadata,
        )

        instance = cls.__new__(cls)
        instance.documents = list(documents)
        instance.method = cast(str, metadata.get("method", "lucene"))
        instance.k1 = cls._metadata_float(metadata, "k1", 1.5)
        instance.b = cls._metadata_float(metadata, "b", 0.75)
        instance.delta = cls._metadata_float(metadata, "delta", 0.5)
        instance.tokenizer_name = tokenizer_name
        instance.use_kiwi_tokenizer, instance.kiwi_lexical_candidate_mode = (
            cls._legacy_tokenizer_flags(instance.tokenizer_name)
        )
        instance.tokenizer = (
            create(instance.tokenizer_name) if instance.use_kiwi_tokenizer else None
        )
        instance.corpus_tokens = []
        instance.bm25 = bm25s.BM25.load(path, load_corpus=True)
        return instance
