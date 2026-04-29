from __future__ import annotations

from snowiki.search.analyzer import build_mixed_language_analyzer


def test_mixed_language_analyzer_preserves_real_snowiki_tokens() -> None:
    analyzer = build_mixed_language_analyzer()

    tokens = set(
        analyzer.tokenize(
            "## 한국어 Retrieval\n"
            "src/snowiki/search/workspace.py uses build_retrieval_snapshot, "
            "SearchDocument, kebab-case, package.module.symbol, "
            "and snowiki benchmark --top-k 5 --target bm25_regex_v1."
        )
    )

    assert {
        "한국어",
        "한국",
        "retrieval",
        "src/snowiki/search/workspace.py",
        "src",
        "snowiki",
        "search",
        "workspace",
        "py",
        "build_retrieval_snapshot",
        "build",
        "snapshot",
        "searchdocument",
        "document",
        "kebab-case",
        "kebab",
        "case",
        "package.module.symbol",
        "package",
        "module",
        "symbol",
        "--top-k",
        "top-k",
        "top",
        "--target",
        "target",
        "bm25_regex_v1",
        "bm25",
        "regex",
        "v1",
        "5",
    } <= tokens


def test_mixed_language_analyzer_normalizes_case_and_unicode() -> None:
    analyzer = build_mixed_language_analyzer()

    assert analyzer.normalize("Ｓｎｏｗｉｋｉ   QUERY") == "snowiki query"
    assert analyzer.tokenize("") == ()
