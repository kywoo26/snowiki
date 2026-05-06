from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from .models import SearchHit

if TYPE_CHECKING:
    from .bm25_index import BM25SearchIndex
    from .registry import TokenizerSpec


TOKEN_EXPLAIN_TRACE_SCHEMA_VERSION = "experimental.token_explain.v1"
TOKEN_EXPLAIN_TRACE_STAGES = ["normalization", "tokenization", "search"]


def build_token_explain_trace(
    index: BM25SearchIndex,
    query_text: str,
    hits: Sequence[SearchHit],
    tokenizer_spec: TokenizerSpec,
    *,
    tokenizer_config: dict[str, object] | None = None,
    max_query_tokens: int = 128,
    max_returned_docs: int = 5,
    max_matched_terms_per_doc: int = 64,
) -> dict[str, object]:
    query_tokens = index.tokenize_query(query_text)
    traced_hits = hits[:max_returned_docs]

    matched_terms: list[dict[str, object]] = []
    matched_terms_truncated = False
    for rank, hit in enumerate(traced_hits, start=1):
        terms = list(hit.matched_terms[:max_matched_terms_per_doc])
        if len(hit.matched_terms) > max_matched_terms_per_doc:
            matched_terms_truncated = True
        matched_terms.append(
            {
                "rank": rank,
                "doc_id": hit.document.id,
                "terms": terms,
            }
        )

    config = tokenizer_config if tokenizer_config is not None else {
        "family": tokenizer_spec.family,
        "runtime_supported": tokenizer_spec.runtime_supported,
    }

    return {
        "schema_version": TOKEN_EXPLAIN_TRACE_SCHEMA_VERSION,
        "analyzer_name": "bm25",
        "tokenizer_name": tokenizer_spec.name,
        "tokenizer_version": tokenizer_spec.version,
        "tokenizer_config": config,
        "query_tokens": list(query_tokens[:max_query_tokens]),
        "matched_terms": matched_terms,
        "stages": list(TOKEN_EXPLAIN_TRACE_STAGES),
        "limits": {
            "max_query_tokens": max_query_tokens,
            "max_traced_returned_docs": max_returned_docs,
            "max_matched_terms_per_doc": max_matched_terms_per_doc,
        },
        "truncated": {
            "query_tokens": len(query_tokens) > max_query_tokens,
            "returned_docs": len(hits) > max_returned_docs,
            "matched_terms": matched_terms_truncated,
        },
    }
