from __future__ import annotations

from collections.abc import Sequence

from ..models import SearchHit
from ..protocols import RuntimeSearchIndex
from ..requests import RuntimeSearchRequest
from .policies import KNOWN_ITEM_POLICY


def known_item_lookup(
    index: RuntimeSearchIndex,
    query: str,
    *,
    limit: int = 10,
) -> list[SearchHit]:
    request = RuntimeSearchRequest(
        query=query,
        candidate_limit=KNOWN_ITEM_POLICY.candidate_limit(limit),
        exact_path_bias=KNOWN_ITEM_POLICY.exact_path_bias,
        kind_weights=KNOWN_ITEM_POLICY.kind_weights,
    )
    hits: Sequence[SearchHit] = index.search(request)
    return list(hits)[:limit]
