from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from .specs import QueryResult


def normalize_query_results(raw_results: object) -> tuple[QueryResult, ...]:
    """Normalize benchmark retrieval results into QueryResult values."""
    if not isinstance(raw_results, Sequence) or isinstance(raw_results, str | bytes):
        raise TypeError("Benchmark results must be a sequence.")
    query_results: list[QueryResult] = []
    for item in raw_results:
        if isinstance(item, QueryResult):
            query_results.append(item)
            continue
        if not isinstance(item, tuple):
            raise TypeError(
                "Benchmark result items must be QueryResult values or (query_id, ranked_doc_ids) tuples."
            )
        tuple_item = cast(tuple[object, ...], item)
        if len(tuple_item) != 2:
            raise TypeError(
                "Benchmark result items must be QueryResult values or (query_id, ranked_doc_ids) tuples."
            )
        query_id, ranked_doc_ids = tuple_item
        if not isinstance(query_id, str):
            raise TypeError("Benchmark result query IDs must be strings.")
        if not isinstance(ranked_doc_ids, Sequence) or isinstance(
            ranked_doc_ids, str | bytes
        ):
            raise TypeError("Benchmark ranked results must be sequences of doc IDs.")
        query_results.append(
            QueryResult(
                query_id=query_id,
                ranked_doc_ids=tuple(str(doc_id) for doc_id in ranked_doc_ids),
            )
        )
    return tuple(query_results)
