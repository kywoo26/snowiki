from __future__ import annotations

from dataclasses import dataclass

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
