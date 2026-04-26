from __future__ import annotations

from collections.abc import Sequence

from ..indexer import SearchHit
from ..protocols import RuntimeSearchIndex
from ..rerank import NoOpReranker, Reranker


def known_item_lookup(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    reranker: Reranker | None = None,
) -> list[SearchHit]:
    reranker = reranker or NoOpReranker()
    hits: Sequence[SearchHit] = index.search(
        query,
        limit=limit * 3,
        exact_path_bias=True,
        kind_weights={"session": 1.15, "page": 0.85},
    )
    return reranker.rerank(query, list(hits))[:limit]
