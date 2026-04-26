from __future__ import annotations

from collections.abc import Sequence

from ..indexer import SearchHit
from ..protocols import RuntimeSearchIndex
from ..rerank import NoOpReranker, Reranker, blend_hits_by_kind


def topical_recall(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    blend_kinds: bool = True,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    reranker = reranker or NoOpReranker()
    hits: Sequence[SearchHit] = index.search(
        query,
        limit=limit * 4,
        kind_weights={"session": 1.0, "page": 1.0},
    )
    ranked = reranker.rerank(query, list(hits))
    if blend_kinds:
        ranked = blend_hits_by_kind(ranked, limit=limit)
    return ranked[:limit]
