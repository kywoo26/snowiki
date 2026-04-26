from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from snowiki.search.contract import run_authoritative_recall
from snowiki.search.indexer import SearchHit
from snowiki.search.queries.known_item import known_item_lookup
from snowiki.search.queries.temporal import temporal_recall
from snowiki.search.queries.topical import topical_recall
from snowiki.search.workspace import RetrievalService, build_retrieval_snapshot


class QueryHitPayload(TypedDict):
    """Serializable query hit payload."""

    id: str
    path: str
    title: str
    kind: str
    source_type: str
    score: float
    matched_terms: list[str]
    summary: str


class RecallHitPayload(TypedDict):
    """Serializable recall hit payload."""

    id: str
    path: str
    title: str
    kind: str
    score: float
    summary: str


class QueryResult(TypedDict):
    """Serializable query command result."""

    query: str
    mode: str
    semantic_backend: str | None
    records_indexed: int
    pages_indexed: int
    hits: list[QueryHitPayload]


class RecallResult(TypedDict):
    """Serializable recall command result."""

    target: str
    strategy: str
    hits: list[RecallHitPayload]



def query_hit_to_payload(hit: SearchHit) -> QueryHitPayload:
    return {
        "id": hit.document.id,
        "path": hit.document.path,
        "title": hit.document.title,
        "kind": hit.document.kind,
        "source_type": hit.document.source_type,
        "score": round(hit.score, 6),
        "matched_terms": list(hit.matched_terms),
        "summary": hit.document.summary,
    }


def recall_hit_to_payload(hit: SearchHit) -> RecallHitPayload:
    return {
        "id": hit.document.id,
        "path": hit.document.path,
        "title": hit.document.title,
        "kind": hit.document.kind,
        "score": round(hit.score, 6),
        "summary": hit.document.summary,
    }


def run_query(root: Path, query: str, *, mode: str, top_k: int) -> QueryResult:
    """Execute a topical query against normalized and compiled content."""
    snapshot = build_retrieval_snapshot(root)
    hits = topical_recall(snapshot.index, query, limit=top_k)
    return {
        "query": query,
        "mode": mode,
        "semantic_backend": None,
        "records_indexed": snapshot.records_indexed,
        "pages_indexed": snapshot.pages_indexed,
        "hits": [query_hit_to_payload(hit) for hit in hits],
    }


def run_recall(root: Path, target: str) -> RecallResult:
    snapshot = RetrievalService.from_root(root)
    hits, strategy = run_authoritative_recall(
        snapshot.index,
        target,
        limit=10,
        known_item_lookup=known_item_lookup,
        temporal_recall=temporal_recall,
        topical_recall=topical_recall,
    )
    return {
        "target": target,
        "strategy": strategy,
        "hits": [recall_hit_to_payload(hit) for hit in hits],
    }
