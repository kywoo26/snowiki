from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[가-힣]+|[a-z0-9]+", re.IGNORECASE)
_PATH_SPLIT_RE = re.compile(r"[/\\._:-]+")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _is_hangul(token: str) -> bool:
    return all("가" <= char <= "힣" for char in token)


def tokenize_text(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
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


@dataclass(frozen=True)
class RegexTokenizer:
    """Search tokenizer backed by the shipped regex tokenization rules."""

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tokenize_text(text)

    def normalize(self, text: str) -> str:
        return normalize_text(text)


def build_regex_tokenizer() -> RegexTokenizer:
    """Build a fresh regex tokenizer instance."""
    return RegexTokenizer()
