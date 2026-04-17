from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

_BASELINE_ALIAS_MAP = {
    "bm25s_kiwi": "bm25s_kiwi_full",
    "bm25s_kiwi_morphology": "bm25s_kiwi_full",
}


def normalize_benchmark_baseline(name: str) -> str:
    return _BASELINE_ALIAS_MAP.get(name, name)


def normalize_benchmark_baselines(baselines: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for baseline in baselines:
        normalized_name = normalize_benchmark_baseline(baseline)
        if normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)
    return tuple(normalized)


DEFAULT_BASELINES = (
    "lexical",
    "bm25s",
    "bm25s_kiwi_nouns",
    "bm25s_kiwi_full",
)


@dataclass(frozen=True)
class BenchmarkPreset:
    name: str
    description: str
    query_kinds: tuple[str, ...]
    top_k: int = 5
    baselines: tuple[str, ...] = DEFAULT_BASELINES

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "baselines", normalize_benchmark_baselines(self.baselines)
        )


_PRESETS = {
    "core": BenchmarkPreset(
        name="core",
        description="Known-item benchmark slice for fast regression checks.",
        query_kinds=("known-item",),
    ),
    "retrieval": BenchmarkPreset(
        name="retrieval",
        description="Known-item and topical retrieval benchmark coverage.",
        query_kinds=("known-item", "topical"),
    ),
    "full": BenchmarkPreset(
        name="full",
        description="Full benchmark coverage including temporal queries.",
        query_kinds=("known-item", "topical", "temporal"),
    ),
}


def get_preset(name: str) -> BenchmarkPreset:
    key = name.casefold()
    if key not in _PRESETS:
        available = ", ".join(sorted(_PRESETS))
        raise ValueError(
            f"unknown benchmark preset: {name}. Available presets: {available}"
        )
    return _PRESETS[key]


def list_presets() -> tuple[BenchmarkPreset, ...]:
    return tuple(_PRESETS[name] for name in sorted(_PRESETS))
