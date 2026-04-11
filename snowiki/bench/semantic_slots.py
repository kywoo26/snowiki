from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SemanticSlotsConfig:
    enabled: bool = False
    version: str = "v2.1"
    mode: str = "stub"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def expand_query_variants(query: str, config: SemanticSlotsConfig) -> tuple[str, ...]:
    if not config.enabled:
        return (query,)
    normalized = " ".join(query.split())
    return tuple(dict.fromkeys((query, normalized)))


def semantic_slots_status(config: SemanticSlotsConfig) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "version": config.version,
        "mode": config.mode,
        "note": "Semantic slots benchmarking is wired as a V2.1 stub and remains disabled by default.",
    }
