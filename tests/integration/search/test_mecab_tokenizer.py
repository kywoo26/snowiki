from __future__ import annotations

import pytest

from snowiki.search.mecab_tokenizer import MecabSearchTokenizer

pytestmark = pytest.mark.integration


def test_mecab_tokenizer_runs_with_packaged_korean_dictionary() -> None:
    tokenizer = MecabSearchTokenizer()

    tokens = tokenizer.tokenize("안녕하세요 Snowiki 입니다 README.md /foo/bar.py")

    assert "snowiki" in tokens
    assert "readme" in tokens
    assert "foo" in tokens
    assert any(token in {"안녕", "하", "세요", "입니다"} for token in tokens)
