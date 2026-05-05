from __future__ import annotations

from collections.abc import Callable, Sequence

from ..models import SearchHit
from ..protocols import RuntimeSearchIndex
from ..requests import RuntimeSearchRequest
from ..rerank import blend_hits_by_kind
from .policies import TOPICAL_POLICY


def _search_topical_candidates(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int,
) -> Sequence[SearchHit]:
    request = RuntimeSearchRequest(
        query=query,
        candidate_limit=TOPICAL_POLICY.candidate_limit(limit),
        exact_path_bias=TOPICAL_POLICY.exact_path_bias,
        kind_weights=TOPICAL_POLICY.kind_weights,
    )
    return index.search(request)


def execute_topical_search(
    index: RuntimeSearchIndex,
    query: str,
    limit: int = 5,
) -> list[SearchHit]:
    """Canonical topical lexical search executor."""
    hits = _search_topical_candidates(index, query, limit=limit)
    if TOPICAL_POLICY.use_kind_blending:
        hits = blend_hits_by_kind(list(hits), limit=limit)
    return list(hits[:limit])


def topical_recall(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    blend_kinds: bool = True,
    rerank_hits: Callable[[str, list[SearchHit]], list[SearchHit]] | None = None,
) -> list[SearchHit]:
    hits = _search_topical_candidates(index, query, limit=limit)
    ranked = list(hits)
    if rerank_hits is not None:
        ranked = rerank_hits(query, ranked)
    if blend_kinds and TOPICAL_POLICY.use_kind_blending:
        ranked = blend_hits_by_kind(ranked, limit=limit)
    return ranked[:limit]
