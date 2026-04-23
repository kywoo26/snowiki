from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .kiwi_tokenizer import build_bilingual_tokenizer
from .mecab_tokenizer import build_mecab_tokenizer
from .subword_tokenizer import build_wordpiece_tokenizer
from .tokenizer import build_regex_tokenizer

DEFAULT_TOKENIZER_NAME = "regex_v1"


class SearchTokenizer(Protocol):
    """Canonical search tokenizer interface for runtime and benchmark use."""

    def tokenize(self, text: str) -> tuple[str, ...]: ...

    def normalize(self, text: str) -> str: ...


type TokenizerFactory = Callable[[], SearchTokenizer]


@dataclass(frozen=True)
class TokenizerSpec:
    """Immutable metadata for a registered tokenizer candidate."""

    name: str
    family: str
    version: int
    runtime_supported: bool


class TokenizerRegistry:
    """Factory registry for canonical tokenizer candidates."""

    def __init__(self, *, default_name: str) -> None:
        self._default_name: str = default_name
        self._specs: dict[str, TokenizerSpec] = {}
        self._factories: dict[str, TokenizerFactory] = {}

    def register(self, spec: TokenizerSpec, factory: TokenizerFactory) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Tokenizer already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._factories[spec.name] = factory

    def get(self, name: str) -> TokenizerSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tokenizer: {name}") from exc

    def create(self, name: str) -> SearchTokenizer:
        spec = self.get(name)
        tokenizer = self._factories[spec.name]()
        return tokenizer

    def default(self) -> TokenizerSpec:
        return self.get(self._default_name)

    def all_candidates(self) -> tuple[TokenizerSpec, ...]:
        return tuple(self._specs.values())


def is_tokenizer_compatible(stored: str | None, requested: str) -> bool:
    """Return whether a stored tokenizer identity matches the requested one."""
    if stored is None:
        return False
    return stored == requested


TOKENIZER_REGISTRY = TokenizerRegistry(default_name=DEFAULT_TOKENIZER_NAME)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="regex_v1",
        family="regex",
        version=1,
        runtime_supported=True,
    ),
    build_regex_tokenizer,
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="kiwi_morphology_v1",
        family="kiwi",
        version=1,
        runtime_supported=False,
    ),
    lambda: build_bilingual_tokenizer("morphology"),
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="kiwi_nouns_v1",
        family="kiwi",
        version=1,
        runtime_supported=False,
    ),
    lambda: build_bilingual_tokenizer("nouns"),
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="mecab_morphology_v1",
        family="mecab",
        version=1,
        runtime_supported=False,
    ),
    build_mecab_tokenizer,
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="hf_wordpiece_v1",
        family="subword",
        version=1,
        runtime_supported=False,
    ),
    build_wordpiece_tokenizer,
)


def register(spec: TokenizerSpec, factory: TokenizerFactory) -> None:
    """Register a tokenizer spec and fresh-instance factory."""
    TOKENIZER_REGISTRY.register(spec, factory)


def get(name: str) -> TokenizerSpec:
    """Return the spec for a registered tokenizer."""
    return TOKENIZER_REGISTRY.get(name)


def create(name: str) -> SearchTokenizer:
    """Create a fresh tokenizer instance from the registry."""
    return TOKENIZER_REGISTRY.create(name)


def default() -> TokenizerSpec:
    """Return the default runtime tokenizer spec."""
    return TOKENIZER_REGISTRY.default()


def all_candidates() -> tuple[TokenizerSpec, ...]:
    """List registered tokenizer specs."""
    return TOKENIZER_REGISTRY.all_candidates()
