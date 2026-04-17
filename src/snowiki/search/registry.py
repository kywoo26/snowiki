from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from .kiwi_tokenizer import build_korean_tokenizer
from .tokenizer import build_regex_tokenizer

type TokenizerScope = Literal["all", "benchmark", "runtime"]

DEFAULT_TOKENIZER_NAME = "regex_v1"
_BENCHMARK_ALIAS_MAP = {
    "bm25s_kiwi": "kiwi_morphology_v1",
    "bm25s_kiwi_full": "kiwi_morphology_v1",
    "bm25s_kiwi_morphology": "kiwi_morphology_v1",
    "bm25s_kiwi_nouns": "kiwi_nouns_v1",
    "regex": "regex_v1",
    "kiwi": "kiwi_morphology_v1",
}


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
    benchmark_supported: bool


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

    def all_candidates(
        self, scope: TokenizerScope | str = "all"
    ) -> tuple[TokenizerSpec, ...]:
        candidates = tuple(self._specs.values())
        if scope == "all":
            return candidates
        if scope == "runtime":
            return tuple(spec for spec in candidates if spec.runtime_supported)
        if scope == "benchmark":
            return tuple(spec for spec in candidates if spec.benchmark_supported)
        raise ValueError(f"Unknown tokenizer scope: {scope}")


def resolve_legacy_tokenizer(
    use_kiwi_tokenizer: bool | None = None,
    kiwi_lexical_candidate_mode: str | None = None,
    benchmark_alias: str | None = None,
) -> str | None:
    """Map legacy tokenizer flags and aliases to canonical tokenizer names."""
    if benchmark_alias is not None:
        return _BENCHMARK_ALIAS_MAP.get(benchmark_alias)

    if use_kiwi_tokenizer is False:
        return DEFAULT_TOKENIZER_NAME

    if use_kiwi_tokenizer is True:
        if kiwi_lexical_candidate_mode == "nouns":
            return "kiwi_nouns_v1"
        return "kiwi_morphology_v1"

    return DEFAULT_TOKENIZER_NAME


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
        benchmark_supported=True,
    ),
    build_regex_tokenizer,
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="kiwi_morphology_v1",
        family="kiwi",
        version=1,
        runtime_supported=False,
        benchmark_supported=True,
    ),
    lambda: build_korean_tokenizer("morphology"),
)
TOKENIZER_REGISTRY.register(
    TokenizerSpec(
        name="kiwi_nouns_v1",
        family="kiwi",
        version=1,
        runtime_supported=False,
        benchmark_supported=True,
    ),
    lambda: build_korean_tokenizer("nouns"),
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


def all_candidates(scope: TokenizerScope | str = "all") -> tuple[TokenizerSpec, ...]:
    """List registered tokenizer specs for a given support scope."""
    return TOKENIZER_REGISTRY.all_candidates(scope)
