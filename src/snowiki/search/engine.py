from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from .models import SearchDocument, SearchHit
from .registry import SearchTokenizer, create, default
from .requests import RuntimeSearchRequest
from .scoring import HitScorer, RuntimeScoringPolicy

if TYPE_CHECKING:
    from datetime import datetime

    from .bm25_index import BM25SearchIndex


class BM25RuntimeIndex:
    """Runtime BM25 candidate generator with SearchHit-compatible output."""

    def __init__(
        self,
        documents: Iterable[SearchDocument],
        *,
        tokenizer_name: str | None = None,
        tokenizer: SearchTokenizer | None = None,
        scoring_policy: HitScorer | None = None,
    ) -> None:
        self._corpus: tuple[SearchDocument, ...] = tuple(documents)
        self._tokenizer_name: str = tokenizer_name or default().name
        self._tokenizer: SearchTokenizer = tokenizer or create(self._tokenizer_name)
        self._scoring_policy: HitScorer = scoring_policy or RuntimeScoringPolicy()
        self._bm25: BM25SearchIndex = self._build_bm25(self._corpus)

    @property
    def tokenizer(self) -> SearchTokenizer:
        return self._tokenizer

    @property
    def size(self) -> int:
        return len(self._corpus)

    def search(self, request: RuntimeSearchRequest) -> Sequence[SearchHit]:
        if request.candidate_limit == 0:
            return []

        eligible = self._eligible_corpus(
            recorded_after=request.recorded_after,
            recorded_before=request.recorded_before,
        )
        if not eligible:
            return []

        bm25 = (
            self._bm25
            if len(eligible) == len(self._corpus)
            else self._build_bm25(eligible)
        )
        requested = min(len(eligible), request.candidate_limit)
        candidates = bm25.search(
            request.query,
            limit=requested,
            include_matched_terms=False,
        )
        hits = self._scoring_policy.rank_candidates(
            candidates,
            query=request.query,
            tokenizer=self._tokenizer,
            document_tokens=bm25.tokens_for_document,
            exact_path_bias=request.exact_path_bias,
            kind_weights=request.kind_weights,
        )
        return hits[: request.candidate_limit]

    def _eligible_corpus(
        self,
        *,
        recorded_after: datetime | None,
        recorded_before: datetime | None,
    ) -> tuple[SearchDocument, ...]:
        if recorded_after is None and recorded_before is None:
            return self._corpus
        eligible: list[SearchDocument] = []
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

    def _build_bm25(self, documents: Iterable[SearchDocument]) -> BM25SearchIndex:
        from .bm25_index import BM25SearchIndex

        return BM25SearchIndex(
            documents,
            tokenizer_name=self._tokenizer_name,
            tokenizer=self._tokenizer,
        )
