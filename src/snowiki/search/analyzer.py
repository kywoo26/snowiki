from __future__ import annotations

import re
from dataclasses import dataclass

from .token_util import _is_hangul_token
from .tokenizer import normalize_text

_COMPOUND_RE = re.compile(
    "|".join(
        [
            r"-{0,2}[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+",
            r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+",
            r"[A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+",
            r"[A-Za-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*",
            r"(?:[\w가-힣.-]+/)+[\w가-힣.-]+",
        ]
    ),
)
_TOKEN_RE = re.compile(r"--?[a-z0-9][a-z0-9-]*|[가-힣]+|[a-z0-9]+", re.IGNORECASE)
_SPLIT_RE = re.compile(r"[/\\._:-]+")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _ordered_unique(tokens: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        normalized = normalize_text(token).strip("#")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _compound_parts(token: str) -> list[str]:
    parts: list[str] = []
    for chunk in _SPLIT_RE.split(token.lstrip("-")):
        if not chunk:
            continue
        parts.extend(_CAMEL_BOUNDARY_RE.sub(" ", chunk).split())
    return parts


@dataclass(frozen=True)
class MixedLanguageAnalyzer:
    """Analyzer contract for Snowiki's mixed prose, path, and code corpus."""

    name: str = "mixed_language_v1"

    def tokenize(self, text: str) -> tuple[str, ...]:
        if not text or not text.strip():
            return ()

        tokens: list[str] = []
        for match in _COMPOUND_RE.finditer(text):
            compound = match.group(0)
            tokens.append(compound)
            if compound.startswith("--"):
                tokens.append(compound[2:])
            elif compound.startswith("-"):
                tokens.append(compound[1:])
            tokens.extend(_compound_parts(compound))

        normalized = normalize_text(text)
        for match in _TOKEN_RE.finditer(normalized):
            token = match.group(0)
            tokens.append(token)
            if token.startswith("--"):
                tokens.append(token[2:])
            elif token.startswith("-"):
                tokens.append(token[1:])
            if _is_hangul_token(token) and len(token) > 1:
                tokens.extend(token[index : index + 2] for index in range(len(token) - 1))

        return _ordered_unique(tokens)

    def normalize(self, text: str) -> str:
        return normalize_text(text)


def build_mixed_language_analyzer() -> MixedLanguageAnalyzer:
    """Build the first Snowiki mixed-language analyzer contract implementation."""

    return MixedLanguageAnalyzer()
