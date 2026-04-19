from __future__ import annotations

from snowiki.search.mecab_tokenizer import MecabSearchTokenizer


def test_mecab_tokenizer_preserves_non_korean_signal(monkeypatch) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args = args

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


def test_mecab_tokenizer_normalize_matches_regex_normalizer(monkeypatch) -> None:
    class FakeTagger:
        def __init__(self, args: str) -> None:
            self.args = args

        def parse(self, text: str) -> str:
            return "EOS\n"

    monkeypatch.setattr("snowiki.search.mecab_tokenizer.MeCab.Tagger", FakeTagger)

    tokenizer = MecabSearchTokenizer()

    assert tokenizer.normalize(" Hello\tSnowiki ") == "hello snowiki"
