"""Integration tests for real Kiwi-backed tokenization."""

from __future__ import annotations

import pytest

from snowiki.search.kiwi_tokenizer import BilingualTokenizer, KoreanTokenizer

pytestmark = pytest.mark.integration


def test_tokenize_simple_korean_integration_smoke() -> None:
    tokenizer = KoreanTokenizer()
    result = tokenizer.tokenize("자연어 처리는 재미있습니다")
    assert result
    assert any("자연어" in token for token in result)
    assert "재미있" in result


def test_bilingual_tokenize_korean_integration_smoke() -> None:
    tokenizer = BilingualTokenizer()
    result = tokenizer.tokenize("자연어 처리는 재미있습니다")
    assert result
