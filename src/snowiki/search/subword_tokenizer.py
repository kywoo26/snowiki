from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from tokenizers import BertWordPieceTokenizer

from .tokenizer import normalize_text as regex_normalize_text

_SPECIAL_TOKENS = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
_FALLBACK_TOKEN_RE = re.compile(r"[가-힣]+|[a-z0-9]+", re.IGNORECASE)


def _fallback_tokens(text: str) -> tuple[str, ...]:
    normalized = regex_normalize_text(text)
    return tuple(match.group(0) for match in _FALLBACK_TOKEN_RE.finditer(normalized))


def _clean_wordpiece_token(token: str) -> str:
    if token.startswith("##"):
        return token[2:]
    return token


@dataclass
class WordPieceSearchTokenizer:
    """Benchmark-only subword tokenizer trained on the current corpus."""

    vocab_size: int = 2000
    min_frequency: int = 1
    lowercase: bool = True
    _tokenizer: BertWordPieceTokenizer = field(init=False, repr=False)
    _fitted: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._tokenizer = BertWordPieceTokenizer(
            lowercase=self.lowercase,
            clean_text=False,
            handle_chinese_chars=False,
            strip_accents=False,
        )

    def fit_corpus(self, texts: Iterable[str]) -> None:
        normalized = [
            regex_normalize_text(text) for text in texts if text and text.strip()
        ]
        if not normalized:
            self._fitted = False
            return

        self._tokenizer = BertWordPieceTokenizer(
            lowercase=self.lowercase,
            clean_text=False,
            handle_chinese_chars=False,
            strip_accents=False,
        )
        self._tokenizer.train_from_iterator(
            normalized,
            vocab_size=self.vocab_size,
            min_frequency=self.min_frequency,
            special_tokens=_SPECIAL_TOKENS,
        )
        self._fitted = True

    def tokenize(self, text: str) -> tuple[str, ...]:
        normalized = regex_normalize_text(text)
        if not normalized:
            return ()
        if not self._fitted:
            return _fallback_tokens(normalized)

        encoded = self._tokenizer.encode(normalized, add_special_tokens=False)
        tokens = [
            cleaned
            for token in encoded.tokens
            if token not in _SPECIAL_TOKENS
            and (cleaned := _clean_wordpiece_token(token))
        ]
        return tuple(tokens) if tokens else _fallback_tokens(normalized)

    def __call__(self, text: str) -> list[str]:
        return list(self.tokenize(text))

    def normalize(self, text: str) -> str:
        return regex_normalize_text(text)


def build_wordpiece_tokenizer() -> WordPieceSearchTokenizer:
    return WordPieceSearchTokenizer()
