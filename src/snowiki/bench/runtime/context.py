"""Execution-layer context for the lean benchmark runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

ExecutionLayer = Literal[
    "pr_official_quick", "scheduled_official_standard", "release_proof"
]
SampleMode = Literal["quick", "standard", "full"]

OFFICIAL_METRICS: Final[tuple[str, ...]] = (
    "nDCG@10",
    "Recall@100",
    "MRR@10",
    "P95 latency",
)

_EXECUTION_LAYER_ALIASES: Final[dict[str, ExecutionLayer]] = {
    "scheduled_official_broad": "scheduled_official_standard"
}


@dataclass(frozen=True)
class LayerPolicy:
    """Resolved runtime policy for a benchmark execution layer."""

    sample_mode: SampleMode
    sample_size: int | None
    metrics: tuple[str, ...]
    blocking: bool
    enabled_by_default: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return the legacy dict payload used by existing callers."""

        payload: dict[str, object] = {
            "sample_mode": self.sample_mode,
            "metrics": self.metrics,
            "blocking": self.blocking,
        }
        if self.sample_size is not None:
            payload["sample_size"] = self.sample_size
        if self.enabled_by_default is False:
            payload["enabled_by_default"] = False
        return payload


LAYER_POLICIES: Final[dict[ExecutionLayer, LayerPolicy]] = {
    "pr_official_quick": LayerPolicy(
        sample_mode="quick",
        sample_size=150,
        metrics=OFFICIAL_METRICS,
        blocking=True,
    ),
    "scheduled_official_standard": LayerPolicy(
        sample_mode="standard",
        sample_size=500,
        metrics=OFFICIAL_METRICS,
        blocking=False,
    ),
    "release_proof": LayerPolicy(
        sample_mode="full",
        sample_size=None,
        metrics=OFFICIAL_METRICS,
        blocking=True,
        enabled_by_default=False,
    ),
}


def canonicalize_execution_layer(layer: str) -> ExecutionLayer:
    """Normalize legacy execution-layer aliases to the lean runtime surface."""

    alias = _EXECUTION_LAYER_ALIASES.get(layer)
    if alias is not None:
        return alias
    if layer in LAYER_POLICIES:
        return cast(ExecutionLayer, layer)
    raise ValueError(f"unsupported benchmark layer: {layer}")


def get_execution_layer_policy(layer: ExecutionLayer | str) -> LayerPolicy:
    """Return the policy for a supported execution layer."""

    return LAYER_POLICIES[canonicalize_execution_layer(layer)]
