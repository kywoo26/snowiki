from __future__ import annotations

import importlib.util
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path

import pytest

THIS_DIR = Path(__file__).resolve().parent
CONFTST_PATH = THIS_DIR / "conftest.py"
SPEC = importlib.util.spec_from_file_location("retrieval_conftest", CONFTST_PATH)
assert SPEC is not None and SPEC.loader is not None
retrieval_fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retrieval_fixtures)

pytestmark = pytest.mark.integration


class MixedLanguageRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.search = retrieval_fixtures.load_search_api()
        cls.index = retrieval_fixtures.blended_index()
        cls.queries = retrieval_fixtures.benchmark_queries()
        cls.judgments = retrieval_fixtures.benchmark_judgments()

    def test_known_item_lookup_supports_mixed_language_queries(self) -> None:
        cases = (
            ("basic Claude fixture 위치 알려줘.", "fixtures/claude/basic.jsonl"),
            (
                "qmd search tool_use가 있는 Claude session 찾아줘.",
                "fixtures/claude/with_tools.jsonl",
            ),
            (
                "fixture inventory 계약 테스트를 다루는 기본 OMO 세션은?",
                "fixtures/opencode/basic.db",
            ),
        )

        for query, expected_path in cases:
            with self.subTest(query=query):
                hits = self.search.known_item_lookup(self.index, query, limit=3)

                self.assertTrue(hits)
                self.assertEqual(hits[0].document.path, expected_path)

    def test_topical_recall_blends_session_and_page_results(self) -> None:
        cases = (
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
        )

        for query, expected_path in cases:
            with self.subTest(query=query):
                hits = self.search.topical_recall(self.index, query, limit=4)
                kinds = {hit.document.kind for hit in hits}

                self.assertTrue(hits)
                self.assertEqual(hits[0].document.path, expected_path)
                self.assertIn("session", kinds)
                self.assertIn("page", kinds)

    def test_temporal_recall_prioritizes_recent_window(self) -> None:
        cases = (
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
        )

        for query, expected_path in cases:
            with self.subTest(query=query):
                hits = self.search.temporal_recall(
                    self.index,
                    query,
                    limit=3,
                    reference_time=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
                )

                self.assertTrue(hits)
                self.assertEqual(hits[0].document.path, expected_path)

    def test_benchmark_queries_return_gold_paths(self) -> None:
        for query in self.queries:
            with self.subTest(query_id=query["id"]):
                hits = self.search.known_item_lookup(
                    self.index, str(query["text"]), limit=5
                )
                returned_paths = {hit.document.path for hit in hits}
                gold_paths = set(self.judgments[str(query["id"])])

                self.assertTrue(gold_paths <= returned_paths)
                self.assertIn(hits[0].document.path, gold_paths)

    def test_canonical_ko_mixed_slice_is_fully_supported(self) -> None:
        benchmarks_root = retrieval_fixtures._repo_root() / "benchmarks"
        queries_payload = json.loads(
            (benchmarks_root / "queries.json").read_text(encoding="utf-8")
        )
        canonical_ids = {
            query["id"]
            for query in queries_payload["queries"]
            if query["group"] in {"ko", "mixed"}
        }
        supported_ids = {query["id"] for query in self.queries}

        self.assertEqual(
            supported_ids,
            canonical_ids,
            msg=(
                "retrieval fixtures still support only a subset of the canonical "
                "ko/mixed benchmark slice"
            ),
        )


if __name__ == "__main__":
    unittest.main()
