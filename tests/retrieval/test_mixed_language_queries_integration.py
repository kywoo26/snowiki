from __future__ import annotations

import importlib.util
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
        hits = self.search.known_item_lookup(
            self.index, "basic Claude fixture 위치 알려줘.", limit=3
        )

        self.assertTrue(hits)
        self.assertEqual(hits[0].document.path, "fixtures/claude/basic.jsonl")

    def test_topical_recall_blends_session_and_page_results(self) -> None:
        hits = self.search.topical_recall(
            self.index, "mixed language retrieval 한국어 영어", limit=4
        )
        kinds = {hit.document.kind for hit in hits}

        self.assertIn("session", kinds)
        self.assertIn("page", kinds)

    def test_temporal_recall_prioritizes_recent_window(self) -> None:
        hits = self.search.temporal_recall(
            self.index,
            "What did we work on yesterday for Korean retrieval?",
            limit=3,
            reference_time=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
        )

        self.assertTrue(hits)
        self.assertEqual(
            hits[0].document.path,
            "sessions/2026/04/07/mixed-retrieval-session.json",
        )

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


if __name__ == "__main__":
    unittest.main()
