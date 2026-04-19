from __future__ import annotations

from .bm25_index import BM25SearchDocument, BM25SearchHit, BM25SearchIndex
from .contract import (
    TEMPORAL_KEYWORDS,
    is_temporal_query,
    iso_date_window,
    normalize_direct_search_hits,
    normalize_direct_search_result,
    normalize_lexical_hit,
    normalize_recall_hits,
    normalize_recall_result,
    run_authoritative_recall,
)
from .index_lexical import LexicalIndex, build_lexical_index
from .index_wiki import WikiIndex, build_wiki_index
from .indexer import InvertedIndex, SearchDocument, SearchHit, build_blended_index
from .kiwi_tokenizer import BilingualTokenizer, KoreanTokenizer
from .queries.known_item import known_item_lookup
from .queries.temporal import temporal_recall
from .queries.topical import topical_recall
from .registry import (
    DEFAULT_TOKENIZER_NAME,
    SearchTokenizer,
    TokenizerSpec,
    all_candidates,
    create,
    default,
    get,
    is_tokenizer_compatible,
    register,
    resolve_legacy_tokenizer,
)
from .rerank import NoOpReranker
from .semantic_abstraction import DisabledSemanticBackend, SemanticBackend
from .subword_tokenizer import WordPieceSearchTokenizer
from .tokenizer import tokenize_text
from .workspace import RetrievalService, RetrievalSnapshot

__all__ = [
    "BM25SearchDocument",
    "BM25SearchHit",
    "BM25SearchIndex",
    "BilingualTokenizer",
    "DisabledSemanticBackend",
    "InvertedIndex",
    "KoreanTokenizer",
    "LexicalIndex",
    "NoOpReranker",
    "TEMPORAL_KEYWORDS",
    "DEFAULT_TOKENIZER_NAME",
    "RetrievalService",
    "RetrievalSnapshot",
    "SearchTokenizer",
    "SearchDocument",
    "SearchHit",
    "SemanticBackend",
    "TokenizerSpec",
    "WordPieceSearchTokenizer",
    "WikiIndex",
    "all_candidates",
    "build_blended_index",
    "build_lexical_index",
    "build_wiki_index",
    "create",
    "default",
    "get",
    "is_temporal_query",
    "is_tokenizer_compatible",
    "iso_date_window",
    "known_item_lookup",
    "normalize_direct_search_hits",
    "normalize_direct_search_result",
    "normalize_lexical_hit",
    "normalize_recall_hits",
    "normalize_recall_result",
    "register",
    "resolve_legacy_tokenizer",
    "run_authoritative_recall",
    "temporal_recall",
    "tokenize_text",
    "topical_recall",
]
