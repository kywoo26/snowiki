from __future__ import annotations

from .analyzer import MixedLanguageAnalyzer, build_mixed_language_analyzer
from .bm25_index import BM25SearchIndex
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
from .engine import BM25RuntimeIndex
from .kiwi_tokenizer import BilingualTokenizer, KoreanTokenizer
from .mecab_tokenizer import MecabSearchTokenizer
from .models import SearchDocument, SearchHit
from .protocols import RuntimeSearchIndex
from .queries.known_item import known_item_lookup
from .queries.temporal import temporal_recall
from .queries.topical import execute_topical_search, topical_recall
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
)
from .runtime_service import RetrievalService, RetrievalSnapshot
from .subword_tokenizer import WordPieceSearchTokenizer
from .tokenizer import tokenize_text

__all__ = [
    "BM25RuntimeIndex",
    "BM25SearchIndex",
    "BilingualTokenizer",
    "KoreanTokenizer",
    "MecabSearchTokenizer",
    "MixedLanguageAnalyzer",
    "TEMPORAL_KEYWORDS",
    "DEFAULT_TOKENIZER_NAME",
    "RetrievalService",
    "RetrievalSnapshot",
    "RuntimeSearchIndex",
    "SearchTokenizer",
    "SearchDocument",
    "SearchHit",
    "TokenizerSpec",
    "WordPieceSearchTokenizer",
    "all_candidates",
    "build_mixed_language_analyzer",
    "create",
    "default",
    "execute_topical_search",
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
    "run_authoritative_recall",
    "temporal_recall",
    "tokenize_text",
    "topical_recall",
]
