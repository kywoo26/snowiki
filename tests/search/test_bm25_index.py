from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from snowiki.search.bm25_index import BM25SearchDocument, BM25SearchHit, BM25SearchIndex


class _Flattenable:
    def __init__(self, values: list[int] | list[float]) -> None:
        self._values = values

    def flatten(self) -> list[int] | list[float]:
        return self._values


@pytest.fixture
def fake_bm25_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, list[dict[str, object]]]:
    calls: dict[str, list[dict[str, object]]] = {
        "tokenize": [],
        "index": [],
        "retrieve": [],
        "kiwi": [],
    }

    class FakeTokenizer:
        def __call__(self, text: str) -> list[str]:
            calls["kiwi"].append({"text": text})
            if "자연어" in text:
                return ["자연어"]
            return []

    class FakeBM25:
        def __init__(self, **kwargs: object) -> None:
            self._doc_count = 0
            self.kwargs = kwargs

        def index(self, corpus_tokens: list[list[str]], **kwargs: object) -> None:
            self._doc_count = len(corpus_tokens)
            calls["index"].append({"corpus_tokens": corpus_tokens, **kwargs})

        def retrieve(
            self, query_tokens: list[list[str]], **kwargs: object
        ) -> tuple[_Flattenable, _Flattenable]:
            calls["retrieve"].append({"query_tokens": query_tokens, **kwargs})
            limit = min(cast(int, kwargs["k"]), self._doc_count)
            return _Flattenable(list(range(limit))), _Flattenable([1.0] * limit)

    def fake_tokenize(texts: str | list[str], **kwargs: object) -> list[list[str]]:
        calls["tokenize"].append({"texts": texts, **kwargs})
        values = [texts] if isinstance(texts, str) else texts
        return [str(text).lower().replace(".", "").split() for text in values]

    monkeypatch.setattr(
        "snowiki.search.bm25_index.bm25s",
        SimpleNamespace(BM25=FakeBM25, tokenize=fake_tokenize),
    )
    monkeypatch.setattr("snowiki.search.bm25_index.KoreanTokenizer", FakeTokenizer)
    return calls


class TestBM25SearchIndex:
    """Test cases for BM25SearchIndex."""

    def test_init_empty(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        index = BM25SearchIndex([])
        assert index.documents == []
        assert index.method == "lucene"
        assert fake_bm25_backend["tokenize"] == []

    def test_init_with_documents(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            BM25SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test Document",
                content="This is a test document about Python.",
            ),
            BM25SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="Another Document",
                content="This document is about programming.",
            ),
        ]
        index = BM25SearchIndex(docs)
        assert len(index.documents) == 2
        assert index.method == "lucene"
        assert len(fake_bm25_backend["index"]) == 1

    def test_search_empty_index(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        index = BM25SearchIndex([])
        results = index.search("test")
        assert results == []
        assert fake_bm25_backend["retrieve"] == []

    def test_search_with_results(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            BM25SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Programming",
                content="Python is a great language for programming.",
            ),
            BM25SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="Java Programming",
                content="Java is another programming language.",
            ),
        ]
        index = BM25SearchIndex(docs)
        results = index.search("Python")
        assert len(results) > 0
        assert isinstance(results[0], BM25SearchHit)
        assert results[0].score > 0
        assert len(fake_bm25_backend["retrieve"]) == 1

    def test_search_korean_uses_tokenizer_output(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            BM25SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="자연어 처리",
                content="자연어 처리는 재미있는 분야입니다.",
            ),
            BM25SearchDocument(
                id="doc2",
                path="test/doc2.md",
                kind="summary",
                title="컴퓨터 비전",
                content="컴퓨터 비전은 이미지를 분석합니다.",
            ),
        ]
        index = BM25SearchIndex(docs)
        results = index.search("자연어")
        assert len(results) > 0
        assert isinstance(results[0], BM25SearchHit)
        assert any(call["text"] == "자연어" for call in fake_bm25_backend["kiwi"])

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="Invalid method"):
            BM25SearchIndex([], method="invalid")

    @pytest.mark.parametrize(
        "method", ["robertson", "atire", "bm25l", "bm25+", "lucene"]
    )
    def test_different_methods(
        self,
        method: str,
        fake_bm25_backend: dict[str, list[dict[str, object]]],
    ) -> None:
        docs = [
            BM25SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Test",
                content="Test content.",
            ),
        ]

        index = BM25SearchIndex(docs, method=method, use_kiwi_tokenizer=False)
        assert index.method == method
        results = index.search("test")
        assert isinstance(results, list)
        assert fake_bm25_backend["kiwi"] == []

    def test_search_with_limit(
        self, fake_bm25_backend: dict[str, list[dict[str, object]]]
    ) -> None:
        docs = [
            BM25SearchDocument(
                id=f"doc{i}",
                path=f"test/doc{i}.md",
                kind="summary",
                title=f"Document {i}",
                content=f"Content about topic {i}.",
            )
            for i in range(10)
        ]
        index = BM25SearchIndex(docs)
        results = index.search("topic", limit=5)
        assert len(results) <= 5
        assert fake_bm25_backend["retrieve"][0]["k"] == 5

    def test_bm25s_calls_disable_progress_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tokenize_calls: list[dict[str, object]] = []
        index_calls: list[dict[str, object]] = []
        retrieve_calls: list[dict[str, object]] = []

        class FakeBM25:
            def __init__(self, **kwargs) -> None:
                del kwargs

            def index(self, corpus_tokens, **kwargs) -> None:
                index_calls.append({"corpus_tokens": corpus_tokens, **kwargs})

            def retrieve(self, query_tokens, **kwargs):
                retrieve_calls.append({"query_tokens": query_tokens, **kwargs})
                return (
                    SimpleNamespace(flatten=lambda: [0]),
                    SimpleNamespace(flatten=lambda: [1.0]),
                )

        def fake_tokenize(texts, **kwargs):
            tokenize_calls.append({"texts": texts, **kwargs})
            return [["python"]]

        monkeypatch.setattr(
            "snowiki.search.bm25_index.bm25s",
            SimpleNamespace(BM25=FakeBM25, tokenize=fake_tokenize),
        )

        docs = [
            BM25SearchDocument(
                id="doc1",
                path="test/doc1.md",
                kind="summary",
                title="Python Programming",
                content="Python is a great language for programming.",
            )
        ]

        index = BM25SearchIndex(docs, use_kiwi_tokenizer=False)
        results = index.search("Python")

        assert len(results) == 1
        assert tokenize_calls == [
            {
                "texts": [
                    "Python Programming\nPython is a great language for programming.\n"
                ],
                "stopwords": "en",
                "return_ids": False,
                "show_progress": False,
                "leave": False,
            },
            {
                "texts": "Python",
                "stopwords": "en",
                "return_ids": False,
                "show_progress": False,
                "leave": False,
            },
        ]
        assert index_calls == [
            {
                "corpus_tokens": [["python"]],
                "show_progress": False,
                "leave_progress": False,
            }
        ]
        assert retrieve_calls == [
            {
                "query_tokens": [["python"]],
                "k": 1,
                "show_progress": False,
                "leave_progress": False,
            }
        ]
