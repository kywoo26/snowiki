from __future__ import annotations

import pytest

from snowiki.search.mecab_tokenizer import MecabSearchTokenizer


def test_mecab_tokenizer_preserves_non_korean_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args: str = args

        def parse(self, text: str) -> str:
            fixtures = {
                "안녕하세요": "안녕\tNNG,*,*,*,*,*,*,*\n하\tXSV,*,*,*,*,*,*,*\n세요\tEP+EF,*,*,*,*,*,*,*\nEOS\n",
                "입니다": "입니다\tVCP+EF,*,*,*,*,*,*,*\nEOS\n",
            }
            return fixtures.get(text, "EOS\n")

    monkeypatch.setattr("snowiki.search.mecab_tokenizer.MeCab.Tagger", FakeTagger)

    tokenizer = MecabSearchTokenizer()

    assert tokenizer.tokenize("안녕하세요 Snowiki 입니다 README.md /foo/bar.py") == (
        "snowiki",
        "readme",
        "md",
        "foo",
        "bar",
        "py",
        "안녕",
        "하",
        "세요",
        "입니다",
    )


def test_mecab_tokenizer_filters_search_noise_accusative_particles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args: str = args

        def parse(self, text: str) -> str:
            fixtures = {
                "검색을": "검색\tNNG,행위,T,검색,*,*,*,*\n을\tJKO,*,T,을,*,*,*,*\nEOS\n",
                "찾아줘": "찾\tVV,*,T,찾,*,*,*,*\n아\tEC,*,F,아,*,*,*,*\n줘\tVX+EC,*,F,줘,Inflect,VX,EC,주/VX/*+어/EC/*\nEOS\n",
            }
            return fixtures.get(text, "EOS\n")

    monkeypatch.setattr("snowiki.search.mecab_tokenizer.MeCab.Tagger", FakeTagger)

    tokenizer = MecabSearchTokenizer()

    assert tokenizer.tokenize("qmd 검색을 Bash 찾아줘") == (
        "qmd",
        "bash",
        "검색",
        "찾",
        "아",
        "줘",
    )


def test_mecab_tokenizer_normalize_matches_regex_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args: str = args

        def parse(self, text: str) -> str:
            _ = text
            return "EOS\n"

    monkeypatch.setattr("snowiki.search.mecab_tokenizer.MeCab.Tagger", FakeTagger)

    tokenizer = MecabSearchTokenizer()

    assert tokenizer.normalize(" Hello\tSnowiki ") == "hello snowiki"


def test_mecab_tokenizer_uses_regex_tokens_for_english_only_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args: str = args

        def parse(self, text: str) -> str:
            msg = f"MeCab should not analyze English-only text: {text}"
            raise AssertionError(msg)

    monkeypatch.setattr("snowiki.search.mecab_tokenizer.MeCab.Tagger", FakeTagger)

    tokenizer = MecabSearchTokenizer()

    assert tokenizer.tokenize("Therapeutic use of Dapsone treats pyoderma.") == (
        "therapeutic use of dapsone treats pyoderma",
        "therapeutic",
        "use",
        "of",
        "dapsone",
        "treats",
        "pyoderma",
    )
