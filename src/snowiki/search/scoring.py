from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from .models import SearchDocument, SearchHit


class SearchRuntimeTokenizer(Protocol):
    def tokenize(self, text: str) -> tuple[str, ...]: ...

    def normalize(self, text: str) -> str: ...


class HitScorer(Protocol):
    """Protocol for scoring policy implementations used by the runtime engine."""

    def rank_candidates(
        self,
        candidates: Iterable[SearchHit],
        *,
        query: str,
        tokenizer: SearchRuntimeTokenizer,
        document_tokens: Callable[[str], tuple[str, ...]],
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> list[SearchHit]: ...

    def score_candidate(
        self,
        *,
        document: SearchDocument,
        raw_score: float,
        query_tokens: tuple[str, ...],
        document_tokens: tuple[str, ...],
        tokenizer: SearchRuntimeTokenizer,
        query: str,
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> SearchHit | None: ...

    def sort_key(self, hit: SearchHit) -> tuple[float, float, str, str]: ...


@dataclass(frozen=True, slots=True)
class RuntimeScoringPolicy:
    """Runtime scoring policy for SearchHit-compatible candidates."""

    exact_path_token_boost: float = 2.0
    path_phrase_boost: float = 2.5
    recency_divisor: float = 10_000_000_000.0
    default_kind_weight: float = 1.0

    def rank_candidates(
        self,
        candidates: Iterable[SearchHit],
        *,
        query: str,
        tokenizer: SearchRuntimeTokenizer,
        document_tokens: Callable[[str], tuple[str, ...]],
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> list[SearchHit]:
        query_tokens = tokenizer.tokenize(query)
        hits = [
            hit
            for candidate in candidates
            if (
                hit := self.score_candidate(
                    document=candidate.document,
                    raw_score=candidate.score,
                    query_tokens=query_tokens,
                    document_tokens=document_tokens(candidate.document.id),
                    tokenizer=tokenizer,
                    query=query,
                    exact_path_bias=exact_path_bias,
                    kind_weights=kind_weights,
                )
            )
            is not None
        ]
        hits.sort(key=self.sort_key)
        return hits

    def score_candidate(
        self,
        *,
        document: SearchDocument,
        raw_score: float,
        query_tokens: tuple[str, ...],
        document_tokens: tuple[str, ...],
        tokenizer: SearchRuntimeTokenizer,
        query: str,
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> SearchHit | None:
        query_terms = set(query_tokens)
        document_terms = set(document_tokens)
        matched_terms = tuple(sorted(query_terms & document_terms))
        normalized_query = tokenizer.normalize(query)
        normalized_path = tokenizer.normalize(document.path)
        path_match = bool(normalized_query and normalized_query in normalized_path)
        if raw_score <= 0.0 and not matched_terms and not path_match:
            return None

        score = raw_score
        if exact_path_bias and any(term in normalized_path for term in query_terms):
            score += self.exact_path_token_boost
        if path_match:
            score += self.path_phrase_boost
        if kind_weights is not None:
            score *= kind_weights.get(document.kind, self.default_kind_weight)
        if document.recorded_at is not None:
            score += document.recorded_at.timestamp() / self.recency_divisor

        return SearchHit(
            document=document,
            score=score,
            matched_terms=matched_terms,
        )

    def sort_key(self, hit: SearchHit) -> tuple[float, float, str, str]:
        recorded_at = hit.document.recorded_at
        recency_key = float("inf")
        if recorded_at is not None:
            recency_key = -recorded_at.timestamp()
        return (-hit.score, recency_key, hit.document.path, hit.document.id)
