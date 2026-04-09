"""Korean morphological analysis tokenizer using Kiwi."""

from __future__ import annotations

from kiwipiepy import Kiwi
from kiwipiepy.utils import Stopwords


class KoreanTokenizer:
    """Korean morphological analyzer using Kiwi library.

    This tokenizer performs morphological analysis on Korean text,
    extracting meaningful tokens (nouns, verbs, adjectives) and
    normalizing them to their dictionary forms.

    Args:
        num_workers: Number of parallel workers for tokenization.
            None means use all available cores.
        extract_nouns_only: If True, extract only nouns (NNG, NNP).
            If False, extract nouns, verbs (VV), and adjectives (VA).
        normalize_coda: Normalize coda characters like "될까욬ㅋㅋ" → "될까요"
        split_complex: Split complex words like "고마움" → "고맙" + "음"
        use_stopwords: If True, filter out common stopwords.

    Example:
        >>> tokenizer = KoreanTokenizer()
        >>> tokenizer.tokenize("자연어 처리는 재미있습니다")
        ('자연어', '처리', '재미있')
        >>> tokenizer.tokenize("해도 되나요?")
        ('하', '되')
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
            if isinstance(token, list):
                for t in token:
                    if (
                        hasattr(t, "tag")
                        and hasattr(t, "form")
                        and t.tag in self.target_tags
                    ):
                        result.append(str(t.form))
            elif hasattr(token, "tag") and hasattr(token, "form"):
                if token.tag in self.target_tags:
                    result.append(str(token.form))

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
            if isinstance(token, list):
                for t in token:
                    if hasattr(t, "form"):
                        result.append(str(t.form))
            elif hasattr(token, "form"):
                result.append(str(token.form))
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
        return self.korean_tokenizer.tokenize(text)

    def __call__(self, text: str) -> list[str]:
        """Make tokenizer callable for bm25s compatibility."""
        return list(self.tokenize(text))


def tokenize_text(text: str) -> tuple[str, ...]:
    """Legacy tokenizer function using Kiwi."""
    tokenizer = KoreanTokenizer()
    return tokenizer.tokenize(text)


def normalize_text(text: str) -> str:
    """Normalize text using Kiwi."""
    tokenizer = KoreanTokenizer()
    return tokenizer.normalize(text)
