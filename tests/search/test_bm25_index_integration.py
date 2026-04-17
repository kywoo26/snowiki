from __future__ import annotations

import pytest

from snowiki.search.bm25_index import BM25SearchDocument, BM25SearchHit, BM25SearchIndex

pytestmark = pytest.mark.integration


def test_search_korean_integration_smoke() -> None:
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
    assert results
    assert isinstance(results[0], BM25SearchHit)


def test_search_korean_accepts_canonical_tokenizer_name() -> None:
    docs = [
        BM25SearchDocument(
            id="doc1",
            path="test/doc1.md",
            kind="summary",
            title="자연어 처리",
            content="자연어 처리는 재미있는 분야입니다.",
        )
    ]

    index = BM25SearchIndex(docs, tokenizer_name="kiwi_morphology_v1")

    assert index.tokenizer_name == "kiwi_morphology_v1"
    assert index.search("재미있다")
