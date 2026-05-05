from __future__ import annotations

from collections.abc import Callable, Sequence

from ..models import SearchHit
from ..protocols import RuntimeSearchIndex
from ..requests import RuntimeSearchRequest
from .policies import KNOWN_ITEM_POLICY


def known_item_lookup(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
    rerank_hits: Callable[[str, list[SearchHit]], list[SearchHit]] | None = None,
) -> list[SearchHit]:
    request = RuntimeSearchRequest(
        query=query,
        candidate_limit=KNOWN_ITEM_POLICY.candidate_limit(limit),
        exact_path_bias=KNOWN_ITEM_POLICY.exact_path_bias,
        kind_weights=KNOWN_ITEM_POLICY.kind_weights,
    )
    hits: Sequence[SearchHit] = index.search(request)
    ranked = list(hits)
    if rerank_hits is not None:
        ranked = rerank_hits(query, ranked)
    return ranked[:limit]
