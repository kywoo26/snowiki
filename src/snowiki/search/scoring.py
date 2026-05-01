from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import SearchDocument, SearchHit


@dataclass(frozen=True, slots=True)
class RuntimeScoringPolicy:
    """Runtime scoring policy for SearchHit-compatible candidates."""

    exact_path_token_boost: float = 2.0
    path_phrase_boost: float = 2.5
    recency_divisor: float = 10_000_000_000.0
    default_kind_weight: float = 1.0

    def score_candidate(
        self,
        *,
        document: SearchDocument,
        raw_score: float,
        query_terms: set[str],
        document_terms: set[str],
        normalized_query: str,
        normalized_path: str,
        exact_path_bias: bool = False,
        kind_weights: Mapping[str, float] | None = None,
    ) -> SearchHit | None:
        matched_terms = tuple(sorted(query_terms & document_terms))
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

    def sort_key(self, hit: SearchHit) -> tuple[float, str, str]:
        return (-hit.score, hit.document.path, hit.document.id)
