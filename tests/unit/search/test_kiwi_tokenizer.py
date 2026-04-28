"""Unit tests for Kiwi tokenizer wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from snowiki.search.kiwi_tokenizer import (
    BilingualTokenizer,
    KoreanTokenizer,
    build_korean_tokenizer,
)


def _token(form: str, tag: str) -> SimpleNamespace:
    return SimpleNamespace(form=form, tag=tag)


@pytest.fixture
def fake_kiwi(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    class FakeKiwi:
        def __init__(self, num_workers: int | None = None) -> None:
            calls.append({"init_num_workers": num_workers})

        def tokenize(self, text: str, **kwargs: object) -> list[SimpleNamespace]:
            calls.append({"text": text, **kwargs})
            fixtures: dict[str, list[SimpleNamespace]] = {
                "자연어 처리는 재미있습니다": [
                    _token("자연어", "NNG"),
                    _token("처리", "NNG"),
                    _token("재미있", "VA"),
                ],
                "해도 되나요?": [
                    _token("하", "VV"),
                    _token("되", "VV"),
                ],
                "자연어 처리": [
                    _token("자연어", "NNG"),
                    _token("처리", "NNG"),
                ],
                "Hello world": [
                    _token("hello", "SL"),
                    _token("world", "SL"),
                ],
                "자연어 Python 처리 README.md /src/app.py": [
                    _token("자연어", "NNG"),
                    _token("처리", "NNG"),
                ],
                "될까욬ㅋㅋ": [
                    _token("될까요", "VV"),
                ],
            }
            return fixtures.get(text, [])

    monkeypatch.setattr("snowiki.search.kiwi_tokenizer.Kiwi", FakeKiwi)
    return calls


class TestKoreanTokenizer:
    """Test cases for KoreanTokenizer."""

    def test_tokenize_simple_korean(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert result == ("자연어", "처리", "재미있")
        assert fake_kiwi[1]["text"] == "자연어 처리는 재미있습니다"

    def test_tokenize_verbs(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("해도 되나요?")
        assert result == ("하", "되")
        assert fake_kiwi[1]["text"] == "해도 되나요?"

    def test_tokenize_nouns_only(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer(extract_nouns_only=True)
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert result == ("자연어", "처리")
        assert fake_kiwi[1]["text"] == "자연어 처리는 재미있습니다"

    def test_lexical_candidate_modes_distinguish_same_input(
        self, fake_kiwi: list[dict[str, object]]
    ) -> None:
        morphology = build_korean_tokenizer("morphology")
        nouns = build_korean_tokenizer("nouns")

        assert morphology.tokenize("자연어 처리는 재미있습니다") == (
            "자연어",
            "처리",
            "재미있",
        )
        assert nouns.tokenize("자연어 처리는 재미있습니다") == ("자연어", "처리")
        assert [call["text"] for call in fake_kiwi if "text" in call] == [
            "자연어 처리는 재미있습니다",
            "자연어 처리는 재미있습니다",
        ]

    def test_tokenize_empty_string(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("")
        assert result == ()
        assert fake_kiwi == [{"init_num_workers": None}]

    def test_tokenize_whitespace_only(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.tokenize("   ")
        assert result == ()
        assert fake_kiwi == [{"init_num_workers": None}]

    def test_callable(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer("자연어 처리")
        assert result == ["자연어", "처리"]
        assert fake_kiwi[1]["text"] == "자연어 처리"

    def test_normalize(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.normalize("될까욬ㅋㅋ")
        assert result == "될까요"
        assert fake_kiwi[1]["text"] == "될까욬ㅋㅋ"

    def test_normalize_empty(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = KoreanTokenizer()
        result = tokenizer.normalize("")
        assert result == ""
        assert fake_kiwi == [{"init_num_workers": None}]


class TestBilingualTokenizer:
    """Test cases for BilingualTokenizer."""

    def test_tokenize_korean(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = BilingualTokenizer()
        result = tokenizer.tokenize("자연어 처리는 재미있습니다")
        assert result == ("자연어", "처리", "재미있")
        assert fake_kiwi[1]["text"] == "자연어 처리는 재미있습니다"

    def test_callable(self, fake_kiwi: list[dict[str, object]]) -> None:
        tokenizer = BilingualTokenizer()
        result = tokenizer("Hello world")
        assert result == ["hello world", "hello", "world"]
        assert fake_kiwi == [{"init_num_workers": None}]

    def test_english_only_text_skips_kiwi_analysis(
        self, fake_kiwi: list[dict[str, object]]
    ) -> None:
        tokenizer = BilingualTokenizer()

        result = tokenizer.tokenize("Therapeutic use of Dapsone treats pyoderma.")

        assert result == (
            "therapeutic use of dapsone treats pyoderma",
            "therapeutic",
            "use",
            "of",
            "dapsone",
            "treats",
            "pyoderma",
        )
        assert fake_kiwi == [{"init_num_workers": None}]

    def test_tokenize_true_mixed_text_preserves_english_and_paths(
        self, fake_kiwi: list[dict[str, object]]
    ) -> None:
        tokenizer = BilingualTokenizer()
        result = tokenizer.tokenize("자연어 Python 처리 README.md /src/app.py")
        assert result == ("python", "readme", "md", "src", "app", "py", "자연어", "처리")
        assert fake_kiwi[1]["text"] == "자연어 Python 처리 README.md /src/app.py"
