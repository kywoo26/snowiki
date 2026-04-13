from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Protocol

from snowiki.config import (
    DEFAULT_RUNTIME_LEXICAL_POLICY,
    normalize_runtime_lexical_policy,
)

_TOKEN_RE = re.compile(r"[가-힣]+|[a-z0-9]+", re.IGNORECASE)
_PATH_SPLIT_RE = re.compile(r"[/\\._:-]+")


class _SupportsNormalize(Protocol):
    def normalize(self, text: str) -> str: ...


class _SupportsTokenize(Protocol):
    def tokenize(self, text: str) -> tuple[str, ...]: ...


def _resolve_lexical_policy(lexical_policy: str | None) -> str:
    if lexical_policy is None:
        return DEFAULT_RUNTIME_LEXICAL_POLICY
    return normalize_runtime_lexical_policy(lexical_policy)


def _legacy_normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _is_hangul(token: str) -> bool:
    return all("가" <= char <= "힣" for char in token)


@lru_cache(maxsize=1)
def _korean_mixed_normalizer() -> _SupportsNormalize:
    from .kiwi_tokenizer import KoreanTokenizer

    return KoreanTokenizer()


@lru_cache(maxsize=1)
def _korean_mixed_tokenizer() -> _SupportsTokenize:
    from .kiwi_tokenizer import BilingualTokenizer

    return BilingualTokenizer()


def normalize_text(text: str, *, lexical_policy: str | None = None) -> str:
    effective_policy = _resolve_lexical_policy(lexical_policy)
    if effective_policy == "korean-mixed-lexical":
        return _korean_mixed_normalizer().normalize(text)
    return _legacy_normalize_text(text)


def _legacy_tokenize_text(text: str) -> tuple[str, ...]:
    normalized = _legacy_normalize_text(text)
    tokens: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        token = token.strip()
        if not token or token in seen:
            return
        seen.add(token)
        tokens.append(token)

    for chunk in _PATH_SPLIT_RE.split(normalized):
        if chunk:
            add(chunk)

    for match in _TOKEN_RE.finditer(normalized):
        token = match.group(0)
        add(token)
        if _is_hangul(token) and len(token) > 1:
            for index in range(len(token) - 1):
                add(token[index : index + 2])

    return tuple(tokens)


def tokenize_text(text: str, *, lexical_policy: str | None = None) -> tuple[str, ...]:
    effective_policy = _resolve_lexical_policy(lexical_policy)
    if effective_policy == "korean-mixed-lexical":
        return _korean_mixed_tokenizer().tokenize(text)
    return _legacy_tokenize_text(text)
