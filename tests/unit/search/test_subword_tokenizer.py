from __future__ import annotations

from pathlib import Path

from snowiki.search.subword_tokenizer import WordPieceSearchTokenizer


def test_wordpiece_tokenizer_falls_back_before_fit() -> None:
    tokenizer = WordPieceSearchTokenizer()

    assert tokenizer.tokenize("자연어 Python 처리") == ("자연어", "python", "처리")


def test_wordpiece_tokenizer_trains_on_corpus_and_tokenizes() -> None:
    tokenizer = WordPieceSearchTokenizer()
    tokenizer.fit_corpus(
        [
            "Snowiki personal wiki qmd search",
            "자연어 Python 처리 README md src app py",
        ]
    )

    tokens = tokenizer.tokenize("Python README.md")

    assert tokens
    assert any(token in {"python", "readme", "md"} for token in tokens)


def test_wordpiece_tokenizer_save_load_preserves_trained_vocabulary(
    tmp_path: Path,
) -> None:
    tokenizer = WordPieceSearchTokenizer(vocab_size=64)
    tokenizer.fit_corpus(
        [
            "Snowiki personal wiki qmd search",
            "자연어 Python 처리 README md src app py",
        ]
    )
    expected = tokenizer.tokenize("Python README.md")

    vocab_path = tokenizer.save_vocab(tmp_path, prefix="snowiki-wordpiece")
    assert vocab_path is not None
    loaded = WordPieceSearchTokenizer.from_vocab_file(vocab_path, vocab_size=64)

    assert loaded.is_fitted is True
    assert loaded.tokenize("Python README.md") == expected
