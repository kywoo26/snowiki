from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from snowiki.bench.datasets import load_matrix
from snowiki.config import resolve_repo_asset_path

KOREAN_CJK_QUERY_IDS = frozenset(
    {
        "ko_spacing_personal_wiki_compounding",
        "ko_spacing_source_layer_contract",
        "cjk_mixed_code_bm25_cache",
        "ko_long_privacy_secret_redaction",
        "ko_long_source_provenance_contract",
    }
)
REQUIRED_KO_CJK_TAGS = frozenset(
    {
        "ko-spacing",
        "ko-inflection",
        "cjk-mixed-code",
        "long-natural-question",
    }
)
JUDGMENT_EVIDENCE_ENTRY_KEYS = frozenset(
    {
        "query_id",
        "doc_id",
        "relevance",
        "source_file",
        "excerpt",
        "rationale",
        "tags",
    }
)


def test_snowiki_regression_queries_are_reviewable_and_balanced() -> None:
    queries = _load_queries()

    assert len(queries) == 28
    assert len({query["id"] for query in queries}) == len(queries)
    assert {query["group"] for query in queries} == {"ko", "en", "mixed"}
    assert {query["kind"] for query in queries} == {"known-item", "topical", "temporal"}
    assert {
        tag for query in queries for tag in cast(list[str], query.get("tags", []))
    } >= REQUIRED_KO_CJK_TAGS
    assert _tagged_query_ids(queries, "identifier-path-code-heavy") >= {
        "ko_tool_session_qmd",
        "en_benchmark_gate_cli",
        "identifier_bm25_index",
        "identifier_workspace_snapshot",
        "cli_tool_command",
    }
    assert _tagged_query_ids(queries, "hard-negative") >= {
        "ko_privacy_reasoning",
        "ko_analyzer_inflection_quality",
        "ko_privacy_redaction_inflection",
        "ko_source_provenance_inflection",
        "en_judgments_not_diff_session",
        "hard_negative_secret_fixture",
    }
    assert _tagged_query_ids(queries, "ko-spacing") >= {
        "ko_spacing_personal_wiki_compounding",
        "ko_spacing_source_layer_contract",
    }
    assert _tagged_query_ids(queries, "ko-inflection") >= {
        "ko_analyzer_inflection_quality",
        "ko_privacy_redaction_inflection",
        "ko_source_provenance_inflection",
    }
    assert _tagged_query_ids(queries, "cjk-mixed-code") >= {
        "ko_tool_session_qmd",
        "cjk_mixed_code_bm25_cache",
    }
    assert _tagged_query_ids(queries, "long-natural-question") >= {
        "ko_long_privacy_secret_redaction",
        "ko_long_source_provenance_contract",
    }


def test_snowiki_regression_judgments_cover_each_query() -> None:
    queries = _load_queries()
    judgments = _load_judgments()
    corpus_doc_ids = _load_corpus_doc_ids()

    query_ids = {str(query["id"]) for query in queries}
    assert set(judgments) == query_ids
    assert all(judgments[query_id] for query_id in query_ids)
    assert {doc_id for doc_ids in judgments.values() for doc_id in doc_ids} <= corpus_doc_ids
    assert {"cli_tool_command", "session_history", "source_provenance"} <= query_ids


def test_snowiki_regression_judgment_evidence_covers_new_queries() -> None:
    ledger_entries = _load_judgment_evidence()
    entries_by_query_id = {str(entry["query_id"]): entry for entry in ledger_entries}

    assert set(entries_by_query_id) >= KOREAN_CJK_QUERY_IDS
    for query_id in KOREAN_CJK_QUERY_IDS:
        assert set(entries_by_query_id[query_id]) == JUDGMENT_EVIDENCE_ENTRY_KEYS


def test_snowiki_regression_matrix_query_cap_matches_query_count() -> None:
    queries = _load_queries()
    matrix = load_matrix(
        resolve_repo_asset_path(Path("benchmarks/contracts/snowiki_regression_matrix.yaml"))
    )

    assert matrix.levels["regression"].query_cap == len(queries) == 28


def test_snowiki_regression_queries_avoid_path_only_exact_match_bias() -> None:
    queries = _load_queries()
    judgments = _load_judgments()

    path_only_queries = []
    for query in queries:
        query_text = str(query["text"])
        relevant_doc_ids = judgments[str(query["id"])]
        if any(query_text == doc_id for doc_id in relevant_doc_ids):
            path_only_queries.append(str(query["id"]))

    assert path_only_queries == []


def _load_queries() -> list[dict[str, object]]:
    payload = json.loads(_asset_path("queries.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    queries = payload["queries"]
    assert isinstance(queries, list)
    return cast(list[dict[str, object]], queries)


def _load_judgments() -> dict[str, list[str]]:
    payload = json.loads(_asset_path("judgments.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    judgments = payload["judgments"]
    assert isinstance(judgments, dict)
    return cast(dict[str, list[str]], judgments)


def _load_judgment_evidence() -> list[dict[str, object]]:
    payload = json.loads(_asset_path("judgment-evidence.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return cast(list[dict[str, object]], payload)


def _load_corpus_doc_ids() -> set[str]:
    payload = json.loads(_asset_path("corpus.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    corpus = payload["corpus"]
    assert isinstance(corpus, list)
    return {str(row["docid"]) for row in cast(list[dict[str, object]], corpus)}


def _tagged_query_ids(queries: list[dict[str, object]], tag: str) -> set[str]:
    return {
        str(query["id"])
        for query in queries
        if tag in cast(list[str], query.get("tags", []))
    }


def _asset_path(name: str) -> Path:
    return resolve_repo_asset_path(
        Path("benchmarks/regression/snowiki_retrieval/regression") / name
    )
