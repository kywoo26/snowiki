from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from tokenizers import BertWordPieceTokenizer

from .tokenizer import normalize_text as regex_normalize_text

_SPECIAL_TOKENS = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"]
_FALLBACK_TOKEN_RE = re.compile(r"[가-힣]+|[a-z0-9]+", re.IGNORECASE)
DEFAULT_WORDPIECE_VOCAB_SIZE = 30000
DEFAULT_WORDPIECE_MIN_FREQUENCY = 1
DEFAULT_WORDPIECE_LOWERCASE = True


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

    vocab_size: int = DEFAULT_WORDPIECE_VOCAB_SIZE
    min_frequency: int = DEFAULT_WORDPIECE_MIN_FREQUENCY
    lowercase: bool = DEFAULT_WORDPIECE_LOWERCASE
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

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def save_vocab(self, directory: Path, *, prefix: str) -> Path | None:
        if not self._fitted:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        paths = self._tokenizer.save_model(directory.as_posix(), prefix)
        if not paths:
            return None
        return Path(paths[0])

    @classmethod
    def from_vocab_file(
        cls,
        vocab_path: Path,
        *,
        vocab_size: int = DEFAULT_WORDPIECE_VOCAB_SIZE,
        min_frequency: int = DEFAULT_WORDPIECE_MIN_FREQUENCY,
        lowercase: bool = DEFAULT_WORDPIECE_LOWERCASE,
    ) -> WordPieceSearchTokenizer:
        tokenizer = cls(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            lowercase=lowercase,
        )
        tokenizer._tokenizer = BertWordPieceTokenizer.from_file(
            vocab_path.as_posix(),
            lowercase=lowercase,
            clean_text=False,
            handle_chinese_chars=False,
            strip_accents=False,
        )
        tokenizer._fitted = True
        return tokenizer

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


def wordpiece_tokenizer_config() -> dict[str, object]:
    return {
        "lowercase": DEFAULT_WORDPIECE_LOWERCASE,
        "min_frequency": DEFAULT_WORDPIECE_MIN_FREQUENCY,
        "vocab_size": DEFAULT_WORDPIECE_VOCAB_SIZE,
    }
