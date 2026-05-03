from __future__ import annotations

import re

from .tokenizer import normalize_text as regex_normalize_text

_NON_KOREAN_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _ordered_unique(tokens: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _is_hangul_token(token: str) -> bool:
    return bool(token) and all("가" <= char <= "힣" for char in token)


def _contains_hangul(text: str) -> bool:
    return any("가" <= char <= "힣" for char in text)


def _preserve_non_korean_tokens(text: str, *, normalize: bool = False) -> tuple[str, ...]:
    if normalize:
        text = regex_normalize_text(text)
    return tuple(match.group(0) for match in _NON_KOREAN_TOKEN_RE.finditer(text))
