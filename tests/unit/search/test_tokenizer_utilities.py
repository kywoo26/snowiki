from __future__ import annotations

from snowiki.search.analyzer import _ordered_unique as analyzer_ordered_unique
from snowiki.search.kiwi_tokenizer import (
    _ordered_unique as kiwi_ordered_unique,
)
from snowiki.search.kiwi_tokenizer import (
    _preserve_non_korean_tokens as kiwi_preserve_non_korean,
)
from snowiki.search.mecab_tokenizer import (
    _ordered_unique as mecab_ordered_unique,
)
from snowiki.search.mecab_tokenizer import (
    _preserve_non_korean_tokens as mecab_preserve_non_korean,
)
from snowiki.search.token_util import _contains_hangul, _is_hangul_token


class TestOrderedUnique:
    def test_kiwi_ordered_unique_preserves_order_and_deduplicates(self) -> None:
        assert kiwi_ordered_unique(("a", "b", "a", "c")) == ("a", "b", "c")
        assert kiwi_ordered_unique(("한글", "영어", "한글")) == ("한글", "영어")
        assert kiwi_ordered_unique(("src", "app", "py", "src")) == ("src", "app", "py")

    def test_kiwi_ordered_unique_skips_empty_strings(self) -> None:
        assert kiwi_ordered_unique(("a", "", "b", "")) == ("a", "b")
        assert kiwi_ordered_unique(("", "", "")) == ()

    def test_kiwi_ordered_unique_empty_input(self) -> None:
        assert kiwi_ordered_unique(()) == ()

    def test_mecab_ordered_unique_preserves_order_and_deduplicates(self) -> None:
        assert mecab_ordered_unique(("a", "b", "a", "c")) == ("a", "b", "c")
        assert mecab_ordered_unique(("한글", "영어", "한글")) == ("한글", "영어")
        assert mecab_ordered_unique(("src", "app", "py", "src")) == ("src", "app", "py")

    def test_mecab_ordered_unique_skips_empty_strings(self) -> None:
        assert mecab_ordered_unique(("a", "", "b", "")) == ("a", "b")
        assert mecab_ordered_unique(("", "", "")) == ()

    def test_mecab_ordered_unique_empty_input(self) -> None:
        assert mecab_ordered_unique(()) == ()

    def test_analyzer_ordered_unique_preserves_order_and_deduplicates(self) -> None:
        assert analyzer_ordered_unique(["a", "b", "a", "c"]) == ("a", "b", "c")
        assert analyzer_ordered_unique(["한글", "영어", "한글"]) == ("한글", "영어")
        assert analyzer_ordered_unique(["src", "app", "py", "src"]) == ("src", "app", "py")

    def test_analyzer_ordered_unique_skips_empty_strings(self) -> None:
        assert analyzer_ordered_unique(["a", "", "b", ""]) == ("a", "b")
        assert analyzer_ordered_unique(["", "", ""]) == ()

    def test_analyzer_ordered_unique_normalizes_tokens(self) -> None:
        assert analyzer_ordered_unique(["Hello", "World"]) == ("hello", "world")
        assert analyzer_ordered_unique(["#tag", "#TAG"]) == ("tag",)

    def test_analyzer_ordered_unique_empty_input(self) -> None:
        assert analyzer_ordered_unique([]) == ()

    def test_all_ordered_unique_agree_on_non_empty_mixed_input(self) -> None:
        tokens = ("python", "readme", "md", "python", "src", "app", "py")
        kiwi_result = kiwi_ordered_unique(tokens)
        mecab_result = mecab_ordered_unique(tokens)
        assert kiwi_result == mecab_result
        assert kiwi_result == ("python", "readme", "md", "src", "app", "py")


class TestHangulDetection:
    def test_is_hangul_token_all_hangul(self) -> None:
        assert _is_hangul_token("한글") is True
        assert _is_hangul_token("자연어처리") is True
        assert _is_hangul_token("가") is True

    def test_is_hangul_token_mixed_or_non_hangul(self) -> None:
        assert _is_hangul_token("한글abc") is False
        assert _is_hangul_token("python") is False
        assert _is_hangul_token("README") is False
        assert _is_hangul_token("한글123") is False

    def test_is_hangul_token_empty(self) -> None:
        assert _is_hangul_token("") is False

    def test_contains_hangul_with_hangul(self) -> None:
        assert _contains_hangul("한글") is True
        assert _contains_hangul("자연어 처리") is True
        assert _contains_hangul("Python과 한글") is True

    def test_contains_hangul_without_hangul(self) -> None:
        assert _contains_hangul("python") is False
        assert _contains_hangul("README.md") is False
        assert _contains_hangul("12345") is False
        assert _contains_hangul("") is False

    def test_contains_hangul_with_mixed_korean_english_code(self) -> None:
        assert _contains_hangul("src/snowiki/search/workspace.py") is False
        assert _contains_hangul("자연어 Python 처리 README.md") is True
        assert _contains_hangul("build_retrieval_snapshot") is False
        assert _contains_hangul("한국어 Retrieval") is True


class TestPreserveNonKoreanTokens:
    def test_kiwi_preserve_non_korean_extracts_english_and_paths(self) -> None:
        assert kiwi_preserve_non_korean("Python README.md /src/app.py", normalize=True) == (
            "python",
            "readme",
            "md",
            "src",
            "app",
            "py",
        )

    def test_kiwi_preserve_non_korean_lowercases(self) -> None:
        assert kiwi_preserve_non_korean("Python", normalize=True) == ("python",)
        assert kiwi_preserve_non_korean("README", normalize=True) == ("readme",)

    def test_kiwi_preserve_non_korean_strips_punctuation(self) -> None:
        assert kiwi_preserve_non_korean("src/app.py", normalize=True) == ("src", "app", "py")
        assert kiwi_preserve_non_korean("package.module.symbol", normalize=True) == (
            "package",
            "module",
            "symbol",
        )

    def test_kiwi_preserve_non_korean_empty_and_hangul_only(self) -> None:
        assert kiwi_preserve_non_korean("자연어 처리", normalize=True) == ()
        assert kiwi_preserve_non_korean("", normalize=True) == ()

    def test_kiwi_preserve_non_korean_mixed_korean_english_code(self) -> None:
        result = kiwi_preserve_non_korean("자연어 Python 처리 README.md /src/app.py", normalize=True)
        assert "python" in result
        assert "readme" in result
        assert "md" in result
        assert "src" in result
        assert "app" in result
        assert "py" in result

    def test_mecab_preserve_non_korean_extracts_english_and_paths(self) -> None:
        assert mecab_preserve_non_korean("python readme.md /src/app.py") == (
            "python",
            "readme",
            "md",
            "src",
            "app",
            "py",
        )

    def test_mecab_preserve_non_korean_preserves_case(self) -> None:
        assert mecab_preserve_non_korean("Python") == ("Python",)
        assert mecab_preserve_non_korean("README") == ("README",)

    def test_mecab_preserve_non_korean_empty_and_hangul_only(self) -> None:
        assert mecab_preserve_non_korean("자연어 처리") == ()
        assert mecab_preserve_non_korean("") == ()

    def test_kiwi_and_mecab_preserve_agree_on_pre_normalized_input(self) -> None:
        text = "자연어 python 처리 readme.md /src/app.py"
        assert kiwi_preserve_non_korean(text, normalize=True) == mecab_preserve_non_korean(text)

    def test_kiwi_lowercases_while_mecab_expects_pre_normalized(self) -> None:
        mixed = "Python README.md"
        assert kiwi_preserve_non_korean(mixed, normalize=True) == ("python", "readme", "md")
        assert mecab_preserve_non_korean(mixed) == ("Python", "README", "md")
