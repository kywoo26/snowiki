"""Korean morphological analysis tokenizer using Kiwi."""

from __future__ import annotations

import re
from typing import Literal

from kiwipiepy import Kiwi
from kiwipiepy.utils import Stopwords

from .tokenizer import normalize_text as regex_normalize_text
from .tokenizer import tokenize_text as regex_tokenize_text

KiwiLexicalCandidateMode = Literal["morphology", "nouns"]
KIWI_LEXICAL_CANDIDATE_MODES: frozenset[KiwiLexicalCandidateMode] = frozenset(
    ["morphology", "nouns"]
)


_NON_KOREAN_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _token_forms(
    tokens: object, target_tags: frozenset[str] | None = None
) -> list[str]:
    items = tokens if isinstance(tokens, list) else [tokens]
    result: list[str] = []
    for item in items:
        tag = getattr(item, "tag", None)
        form = getattr(item, "form", None)
        if not isinstance(form, str):
            continue
        if target_tags is not None and tag not in target_tags:
            continue
        result.append(form)
    return result


def _is_hangul_token(token: str) -> bool:
    return bool(token) and all("가" <= char <= "힣" for char in token)


def _contains_hangul(text: str) -> bool:
    return any("가" <= char <= "힣" for char in text)


def _ordered_unique(tokens: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


def _preserve_non_korean_tokens(text: str) -> tuple[str, ...]:
    normalized = regex_normalize_text(text)
    return tuple(match.group(0) for match in _NON_KOREAN_TOKEN_RE.finditer(normalized))


def build_korean_tokenizer(
    mode: KiwiLexicalCandidateMode = "morphology",
    *,
    num_workers: int | None = None,
    normalize_coda: bool = True,
    split_complex: bool = False,
    use_stopwords: bool = False,
) -> KoreanTokenizer:
    """Build a Korean tokenizer for a specific lexical candidate mode."""
    if mode not in KIWI_LEXICAL_CANDIDATE_MODES:
        raise ValueError(
            f"Invalid Kiwi lexical candidate mode: {mode}. "
            + f"Must be one of {sorted(KIWI_LEXICAL_CANDIDATE_MODES)}"
        )

    return KoreanTokenizer(
        num_workers=num_workers,
        extract_nouns_only=mode == "nouns",
        normalize_coda=normalize_coda,
        split_complex=split_complex,
        use_stopwords=use_stopwords,
    )


def build_bilingual_tokenizer(
    mode: KiwiLexicalCandidateMode = "morphology",
    *,
    num_workers: int | None = None,
    use_stopwords: bool = False,
) -> BilingualTokenizer:
    """Build a bilingual tokenizer that preserves non-Korean lexical signal."""
    if mode not in KIWI_LEXICAL_CANDIDATE_MODES:
        raise ValueError(
            f"Invalid Kiwi lexical candidate mode: {mode}. "
            + f"Must be one of {sorted(KIWI_LEXICAL_CANDIDATE_MODES)}"
        )
    return BilingualTokenizer(
        num_workers=num_workers,
        extract_nouns_only=mode == "nouns",
        use_stopwords=use_stopwords,
    )


class KoreanTokenizer:
    """Korean morphological analyzer using Kiwi library.

    This tokenizer performs morphological analysis on Korean text,
    extracting meaningful tokens (nouns, verbs, adjectives) and
    normalizing them to their dictionary forms.
    """

    NOUN_TAGS = frozenset(["NNG", "NNP"])
    VERB_TAGS = frozenset(["VV", "VA"])
    EXTRACTABLE_TAGS = frozenset(["NNG", "NNP", "VV", "VA"])

    def __init__(
        self,
        num_workers: int | None = None,
        extract_nouns_only: bool = False,
        normalize_coda: bool = True,
        split_complex: bool = False,
        use_stopwords: bool = False,
    ) -> None:
        self.kiwi = Kiwi(num_workers=num_workers)
        self.stopwords = Stopwords() if use_stopwords else None
        self.extract_nouns_only = extract_nouns_only
        self.normalize_coda = normalize_coda
        self.split_complex = split_complex

        if extract_nouns_only:
            self.target_tags = self.NOUN_TAGS
        else:
            self.target_tags = self.EXTRACTABLE_TAGS

    def tokenize(self, text: str) -> tuple[str, ...]:
        """Tokenize text into morphological units."""
        if not text or not text.strip():
            return ()

        tokens = self.kiwi.tokenize(
            text,
            normalize_coda=self.normalize_coda,
            split_complex=self.split_complex,
            stopwords=self.stopwords,
        )

        result: list[str] = []
        for token in tokens:
            result.extend(_token_forms(token, self.target_tags))

        return tuple(result)

    def __call__(self, text: str) -> list[str]:
        """Make tokenizer callable for bm25s compatibility."""
        return list(self.tokenize(text))

    def normalize(self, text: str) -> str:
        """Normalize text to standard form."""
        if not text or not text.strip():
            return ""

        tokens = self.kiwi.tokenize(text, normalize_coda=True, stopwords=self.stopwords)
        result: list[str] = []
        for token in tokens:
            result.extend(_token_forms(token))
        return "".join(result)


class BilingualTokenizer:
    """Tokenizer for mixed Korean-English text."""

    def __init__(
        self,
        num_workers: int | None = None,
        extract_nouns_only: bool = False,
        use_stopwords: bool = False,
    ) -> None:
        self.korean_tokenizer = KoreanTokenizer(
            num_workers=num_workers,
            extract_nouns_only=extract_nouns_only,
            use_stopwords=use_stopwords,
        )

    def tokenize(self, text: str) -> tuple[str, ...]:
        """Tokenize mixed Korean-English text."""
        if not text or not text.strip():
            return ()
        preserved = _preserve_non_korean_tokens(text)
        if not _contains_hangul(text):
            return regex_tokenize_text(text)
        korean = self.korean_tokenizer.tokenize(text)
        return _ordered_unique(preserved + korean)

    def __call__(self, text: str) -> list[str]:
        """Make tokenizer callable for bm25s compatibility."""
        return list(self.tokenize(text))

    def normalize(self, text: str) -> str:
        return regex_normalize_text(text)


def tokenize_text(text: str) -> tuple[str, ...]:
    """Legacy tokenizer function using Kiwi."""
    tokenizer = KoreanTokenizer()
    return tokenizer.tokenize(text)


def normalize_text(text: str) -> str:
    """Normalize text using Kiwi."""
    tokenizer = KoreanTokenizer()
    return tokenizer.normalize(text)
