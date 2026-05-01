from __future__ import annotations

from collections.abc import Sequence

from ..models import SearchHit
from ..protocols import RuntimeSearchIndex
from ..requests import RuntimeSearchRequest
from ..rerank import NoOpReranker, Reranker, blend_hits_by_kind
from .policies import TOPICAL_POLICY


def topical_recall(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    blend_kinds: bool = True,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    reranker = reranker or NoOpReranker()
    request = RuntimeSearchRequest(
        query=query,
        candidate_limit=TOPICAL_POLICY.candidate_limit(limit),
        exact_path_bias=TOPICAL_POLICY.exact_path_bias,
        kind_weights=TOPICAL_POLICY.kind_weights,
    )
    hits: Sequence[SearchHit] = index.search(request)
    ranked = reranker.rerank(query, list(hits))
    if blend_kinds and TOPICAL_POLICY.use_kind_blending:
        ranked = blend_hits_by_kind(ranked, limit=limit)
    return ranked[:limit]
