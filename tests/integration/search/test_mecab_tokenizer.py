from __future__ import annotations

import pytest

from snowiki.search.bm25_index import BM25SearchDocument, BM25SearchIndex
from snowiki.search.mecab_tokenizer import MecabSearchTokenizer

pytestmark = pytest.mark.integration


def test_mecab_tokenizer_runs_with_packaged_korean_dictionary() -> None:
    tokenizer = MecabSearchTokenizer()

    tokens = tokenizer.tokenize("안녕하세요 Snowiki 입니다 README.md /foo/bar.py")

    assert "snowiki" in tokens
    assert "readme" in tokens
    assert "foo" in tokens
    assert any(token in {"안녕", "하", "세요", "입니다"} for token in tokens)


def test_mecab_identifier_heavy_tool_session_query_ranks_identifier_evidence() -> None:
    documents = [
        BM25SearchDocument(
            id="fixtures/claude/with_tools.jsonl",
            path="fixtures/claude/with_tools.jsonl",
            kind="benchmark_doc",
            title="fixtures/claude/with_tools.jsonl",
            content=(
                "Claude session with tool calls and tool results. It records a Bash "
                "tool_use that runs qmd search during a Snowiki workflow on "
                "2026-04-02. The session is about using command output as "
                "evidence, not about benchmark scores."
            ),
        ),
        BM25SearchDocument(
            id="sessions/2026/04/07/mixed-retrieval-session.json",
            path="sessions/2026/04/07/mixed-retrieval-session.json",
            kind="benchmark_doc",
            title="sessions/2026/04/07/mixed-retrieval-session.json",
            content=(
                "Yesterday retrieval session from 2026-04-07. Work covered "
                "bilingual lexical retrieval, Korean tokenization, mixed "
                "Korean-English query behavior, analyzer candidates, and benchmark "
                "recall tradeoffs. 어제 한국어 검색과 mixed query retrieval 작업을 진행했다."
            ),
        ),
    ]
    index = BM25SearchIndex(
        documents,
        tokenizer_name="mecab_morphology_v1",
        tokenizer=MecabSearchTokenizer(),
    )

    hits = index.search("qmd 검색을 Bash 도구 호출로 실행한 세션 증거를 찾아줘", limit=2)

    assert hits[0].document.id == "fixtures/claude/with_tools.jsonl"
    assert hits[0].matched_terms == ("qmd", "bash")
    assert "을" not in index.tokenize_query(
        "qmd 검색을 Bash 도구 호출로 실행한 세션 증거를 찾아줘"
    )
