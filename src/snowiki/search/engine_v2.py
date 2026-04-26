from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .corpus import RuntimeCorpusDocument
from .indexer import SearchDocument, SearchHit
from .registry import SearchTokenizer, create, default

if TYPE_CHECKING:
    from .bm25_index import BM25SearchIndex

DEFAULT_CANDIDATE_MULTIPLIER = 8


@dataclass(frozen=True)
class _RuntimeCandidate:
    document: SearchDocument
    score: float
    matched_terms: tuple[str, ...]


class BM25RuntimeIndex:
    """Runtime BM25 candidate generator with SearchHit-compatible output."""

    def __init__(
        self,
        documents: Iterable[RuntimeCorpusDocument],
        *,
        tokenizer_name: str | None = None,
        tokenizer: SearchTokenizer | None = None,
        candidate_multiplier: int = DEFAULT_CANDIDATE_MULTIPLIER,
    ) -> None:
        self._corpus: tuple[RuntimeCorpusDocument, ...] = tuple(documents)
        self._search_documents: tuple[SearchDocument, ...] = tuple(
            document.to_search_document() for document in self._corpus
        )
        self._document_by_id: dict[str, SearchDocument] = {
            document.id: document for document in self._search_documents
        }
        self._tokenizer_name: str = tokenizer_name or default().name
        self._tokenizer: SearchTokenizer = tokenizer or create(self._tokenizer_name)
        self._candidate_multiplier: int = max(candidate_multiplier, 1)
        self._document_tokens: dict[str, Counter[str]] = {
            document.id: self._tokenize_document(document)
            for document in self._search_documents
        }
        self._bm25: BM25SearchIndex = self._build_bm25(self._corpus)

    @property
    def tokenizer(self) -> SearchTokenizer:
        return self._tokenizer

    @property
    def size(self) -> int:
        return len(self._corpus)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        kind_weights: Mapping[str, float] | None = None,
        recorded_after: datetime | None = None,
        recorded_before: datetime | None = None,
        exact_path_bias: bool = False,
    ) -> list[SearchHit]:
        query_terms = self._tokenizer.tokenize(query)
        if limit <= 0 or not query_terms:
            return []

        eligible = self._eligible_corpus(
            recorded_after=recorded_after,
            recorded_before=recorded_before,
        )
        if not eligible:
            return []

        bm25 = self._bm25 if len(eligible) == len(self._corpus) else self._build_bm25(eligible)
        candidate_multiplier = (
            self._candidate_multiplier
            if exact_path_bias or self._has_non_default_kind_weight(kind_weights)
            else 1
        )
        requested = min(len(eligible), max(limit * candidate_multiplier, limit))
        candidates = bm25.search(query, limit=requested)
        normalized_query = self._tokenizer.normalize(query)
        runtime_candidates = [
            self._adapt_hit(
                hit_document_id=hit.document.id,
                raw_score=hit.score,
                query_terms=query_terms,
                normalized_query=normalized_query,
                kind_weights=kind_weights,
                exact_path_bias=exact_path_bias,
            )
            for hit in candidates
        ]
        hits = [candidate for candidate in runtime_candidates if candidate is not None]
        hits.sort(key=lambda hit: (-hit.score, hit.document.path, hit.document.id))
        return [
            SearchHit(
                document=hit.document,
                score=hit.score,
                matched_terms=hit.matched_terms,
            )
            for hit in hits[:limit]
        ]

    def _eligible_corpus(
        self,
        *,
        recorded_after: datetime | None,
        recorded_before: datetime | None,
    ) -> tuple[RuntimeCorpusDocument, ...]:
        if recorded_after is None and recorded_before is None:
            return self._corpus
        eligible: list[RuntimeCorpusDocument] = []
        for document in self._corpus:
            if recorded_after is not None and (
                document.recorded_at is None or document.recorded_at < recorded_after
            ):
                continue
            if recorded_before is not None and (
                document.recorded_at is None or document.recorded_at > recorded_before
            ):
                continue
            eligible.append(document)
        return tuple(eligible)

    def _adapt_hit(
        self,
        *,
        hit_document_id: str,
        raw_score: float,
        query_terms: tuple[str, ...],
        normalized_query: str,
        kind_weights: Mapping[str, float] | None,
        exact_path_bias: bool,
    ) -> _RuntimeCandidate | None:
        document = self._document_by_id.get(hit_document_id)
        if document is None:
            return None

        document_tokens = self._document_tokens[document.id]
        matched_terms = tuple(
            sorted(token for token in set(query_terms) if token in document_tokens)
        )
        normalized_path = self._tokenizer.normalize(document.path)
        path_match = bool(normalized_query and normalized_query in normalized_path)
        if raw_score <= 0.0 and not matched_terms and not path_match:
            return None

        score = raw_score
        if exact_path_bias and any(token in normalized_path for token in query_terms):
            score += 2.0
        if path_match:
            score += 2.5
        if kind_weights is not None:
            score *= kind_weights.get(document.kind, 1.0)
        if document.recorded_at is not None:
            score += document.recorded_at.timestamp() / 10_000_000_000.0

        return _RuntimeCandidate(
            document=document,
            score=score,
            matched_terms=matched_terms,
        )

    def _tokenize_document(self, document: SearchDocument) -> Counter[str]:
        tokens: list[str] = []
        for text in (
            document.title,
            document.path,
            document.summary,
            document.content,
            " ".join(document.aliases),
        ):
            tokens.extend(self._tokenizer.tokenize(text))
        return Counter(tokens)

    @staticmethod
    def _has_non_default_kind_weight(kind_weights: Mapping[str, float] | None) -> bool:
        if kind_weights is None:
            return False
        return any(weight != 1.0 for weight in kind_weights.values())

    def _build_bm25(self, documents: Iterable[RuntimeCorpusDocument]) -> BM25SearchIndex:
        from .bm25_index import BM25SearchIndex

        return BM25SearchIndex(
            [document.to_bm25_document() for document in documents],
            tokenizer_name=self._tokenizer_name,
            tokenizer=self._tokenizer,
        )
