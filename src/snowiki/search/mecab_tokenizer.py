from __future__ import annotations

import re
from dataclasses import dataclass, field

import MeCab
import mecab_ko_dic

from .tokenizer import normalize_text as regex_normalize_text

_NON_KOREAN_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_KOREAN_SPAN_RE = re.compile(r"[가-힣]+")
_SEARCH_NOISE_TAG_PREFIXES = ("S",)
_SEARCH_NOISE_TAGS = frozenset({"JKO"})


def _ordered_unique(tokens: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _preserve_non_korean_tokens(normalized_text: str) -> tuple[str, ...]:
    return tuple(
        match.group(0) for match in _NON_KOREAN_TOKEN_RE.finditer(normalized_text)
    )


def _build_mecab_args() -> str:
    dictionary_path = str(mecab_ko_dic.dictionary_path)
    dicrc_path = f"{dictionary_path}/dicrc"
    return f"-r {dicrc_path} -d {dictionary_path}"


def _parse_surface_rows(parsed: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for line in parsed.splitlines():
        if not line or line == "EOS":
            continue
        surface, _, features = line.partition("\t")
        if not surface:
            continue
        pos = features.split(",", 1)[0] if features else ""
        if pos in _SEARCH_NOISE_TAGS or pos.startswith(_SEARCH_NOISE_TAG_PREFIXES):
            continue
        tokens.append(surface)
    return tuple(tokens)


@dataclass
class MecabSearchTokenizer:
    """Benchmark-only Korean Mecab tokenizer with mixed-language preservation."""

    _tagger: MeCab.Tagger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._tagger = MeCab.Tagger(_build_mecab_args())

    def _tokenize_korean_span(self, text: str) -> tuple[str, ...]:
        parsed = self._tagger.parse(text)
        if not parsed:
            return ()
        return _parse_surface_rows(parsed)

    def tokenize(self, text: str) -> tuple[str, ...]:
        normalized = regex_normalize_text(text)
        if not normalized:
            return ()

        preserved = _preserve_non_korean_tokens(normalized)
        korean_tokens: list[str] = []
        for match in _KOREAN_SPAN_RE.finditer(normalized):
            korean_tokens.extend(self._tokenize_korean_span(match.group(0)))
        return _ordered_unique(preserved + tuple(korean_tokens))

    def __call__(self, text: str) -> list[str]:
        return list(self.tokenize(text))

    def normalize(self, text: str) -> str:
        return regex_normalize_text(text)


def build_mecab_tokenizer() -> MecabSearchTokenizer:
    return MecabSearchTokenizer()
