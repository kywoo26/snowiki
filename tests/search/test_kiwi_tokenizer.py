"""Tests for Kiwi tokenizer."""

from __future__ import annotations

import pytest

from snowiki.search.kiwi_tokenizer import BilingualTokenizer, KoreanTokenizer


class TestKoreanTokenizer:
    """Test cases for KoreanTokenizer."""

    def test_tokenize_simple_korean(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert isinstance(result, tuple)
        assert len(result) > 0
        assert any("자연어" in token for token in result)
        assert "재미있" in result

    def test_tokenize_verbs(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("해도 되나요?")
        assert isinstance(result, tuple)
        assert any(token in result for token in ["하", "되"])

    def test_tokenize_nouns_only(self) -> None:
        tokenizer = KoreanTokenizer(extract_nouns_only=True)
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert isinstance(result, tuple)
        assert any("자연어" in token for token in result)
        assert "재미있" not in result

    def test_tokenize_empty_string(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("")
        assert result == ()

    def test_tokenize_whitespace_only(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("   ")
        assert result == ()

    def test_callable(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer("자연어 처리")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_normalize(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.normalize("될까욬ㅋㅋ")
        assert isinstance(result, str)
        assert "ㅋㅋ" not in result or "까요" in result

    def test_normalize_empty(self) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.normalize("")
        assert result == ""


class TestBilingualTokenizer:
    """Test cases for BilingualTokenizer."""

    def test_tokenize_korean(self) -> None:
        tokenizer = BilingualTokenizer()
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert isinstance(result, tuple)
        assert len(result) > 0

    def test_callable(self) -> None:
        tokenizer = BilingualTokenizer()
        result = tokenizer("Hello world")
        assert isinstance(result, list)
