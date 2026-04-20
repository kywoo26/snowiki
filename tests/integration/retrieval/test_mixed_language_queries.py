from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from typing import Any

import pytest

retrieval_fixtures = importlib.import_module("tests.helpers.retrieval_data")


@pytest.fixture(scope="module")
def search_api() -> Any:
    return retrieval_fixtures.load_search_api()


@pytest.fixture(scope="module")
def blended_index() -> Any:
    return retrieval_fixtures.blended_index()


@pytest.fixture(scope="module")
def benchmark_queries() -> list[dict[str, object]]:
    return retrieval_fixtures.benchmark_queries()


@pytest.fixture(scope="module")
def benchmark_judgments() -> dict[str, list[str]]:
    return retrieval_fixtures.benchmark_judgments()


@pytest.mark.parametrize(
    ("query", "expected_path"),
    [
        ("basic Claude fixture 위치 알려줘.", "fixtures/claude/basic.jsonl"),
        (
            "qmd search tool_use가 있는 Claude session 찾아줘.",
            "fixtures/claude/with_tools.jsonl",
        ),
        (
            "fixture inventory 계약 테스트를 다루는 기본 OMO 세션은?",
            "fixtures/opencode/basic.db",
        ),
    ],
)
def test_known_item_lookup_supports_mixed_language_queries(
    search_api: Any, blended_index: Any, query: str, expected_path: str
) -> None:
    hits = search_api.known_item_lookup(blended_index, query, limit=3)

    assert hits
    assert hits[0].document.path == expected_path


@pytest.mark.parametrize(
    ("query", "expected_path"),
    [
        (
            "mixed language retrieval 한국어 영어",
            "compiled/wiki/search/mixed-language-overview.md",
        ),
        (
            "한국어와 영어 혼합 질의를 위해 session/page blended results를 제공한다",
            "compiled/wiki/search/mixed-language-overview.md",
        ),
        (
            "benchmark coverage, query inventory, evaluation planning",
            "compiled/wiki/benchmarks/overview.md",
        ),
    ],
)
def test_topical_recall_blends_session_and_page_results(
    search_api: Any, blended_index: Any, query: str, expected_path: str
) -> None:
    hits = search_api.topical_recall(blended_index, query, limit=4)
    kinds = {hit.document.kind for hit in hits}

    assert hits
    assert hits[0].document.path == expected_path
    assert "session" in kinds
    assert "page" in kinds


@pytest.mark.parametrize(
    ("query", "expected_path"),
    [
        (
            "What did we work on yesterday for Korean retrieval?",
            "sessions/2026/04/07/mixed-retrieval-session.json",
        ),
        (
            "어제 한국어 retrieval 작업은 뭐였지?",
            "sessions/2026/04/07/mixed-retrieval-session.json",
        ),
        (
            "지난 어제 한국어 검색과 mixed query retrieval 작업은 뭐였지?",
            "sessions/2026/04/07/mixed-retrieval-session.json",
        ),
    ],
)
def test_temporal_recall_prioritizes_recent_window(
    search_api: Any, blended_index: Any, query: str, expected_path: str
) -> None:
    hits = search_api.temporal_recall(
        blended_index,
        query,
        limit=3,
        reference_time=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )

    assert hits
    assert hits[0].document.path == expected_path


def test_benchmark_queries_return_gold_paths(
    search_api: Any,
    blended_index: Any,
    benchmark_queries: list[dict[str, object]],
    benchmark_judgments: dict[str, list[str]],
) -> None:
    for query in benchmark_queries:
        hits = search_api.known_item_lookup(blended_index, str(query["text"]), limit=5)
        returned_paths = {hit.document.path for hit in hits}
        gold_paths = set(benchmark_judgments[str(query["id"])])

        assert gold_paths <= returned_paths
        assert hits[0].document.path in gold_paths


def test_canonical_ko_mixed_slice_is_fully_supported(
    benchmark_queries: list[dict[str, object]],
) -> None:
    benchmarks_root = retrieval_fixtures._repo_root() / "benchmarks"
    queries_payload = json.loads(
        (benchmarks_root / "queries.json").read_text(encoding="utf-8")
    )
    canonical_ids = {
        query["id"]
        for query in queries_payload["queries"]
        if query["group"] in {"ko", "mixed"}
    }
    supported_ids = {query["id"] for query in benchmark_queries}

    assert supported_ids == canonical_ids, (
        "retrieval fixtures still support only a subset of the canonical "
        "ko/mixed benchmark slice"
    )
