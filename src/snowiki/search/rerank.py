from __future__ import annotations

from collections import defaultdict, deque
from typing import Protocol

from .indexer import SearchHit


class Reranker(Protocol):
    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]: ...


class NoOpReranker:
    def rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        del query
        return hits


def blend_hits_by_kind(hits: list[SearchHit], *, limit: int) -> list[SearchHit]:
    buckets: dict[str, deque[SearchHit]] = defaultdict(deque)
    for hit in hits:
        buckets[hit.document.kind].append(hit)

    ordered_kinds = tuple(sorted(buckets))
    if len(ordered_kinds) < 2:
        return hits[:limit]

    blended: list[SearchHit] = []
    while len(blended) < limit:
        progressed = False
        for kind in ordered_kinds:
            bucket = buckets[kind]
            if not bucket:
                continue
            blended.append(bucket.popleft())
            progressed = True
            if len(blended) == limit:
                break
        if not progressed:
            break
    return blended
