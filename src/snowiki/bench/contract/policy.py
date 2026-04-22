"""Lean benchmark policy contract.

Supports only the official six-dataset suite and the internal regression harness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from ..runtime.catalog import (
    LanguageAxis,
    OfficialDatasetEntry,
    get_dataset_entry,
    is_official,
    official_suite_dataset_ids,
)
from ..runtime.context import (
    ExecutionLayer,
    canonicalize_execution_layer,
    get_execution_layer_policy,
)

AuthorityClass = Literal["official_suite", "regression_harness"]

REGRESSION_HARNESS_DATASET_ID: Final[str] = "regression"

__all__ = [
    "AuthorityClass",
    "BenchmarkPolicy",
    "ExecutionLayer",
    "LanguageAxis",
    "OfficialDatasetEntry",
    "get_dataset_authority",
    "get_dataset_entry",
    "get_layer_policy",
    "get_quick_pr_suite",
    "get_scheduled_suite",
    "is_local_diagnostic",
    "is_official",
    "is_regression_harness",
    "resolve_policy",
]


@dataclass(frozen=True)
class BenchmarkPolicy:
    """Resolved policy for a benchmark run."""

    layer: ExecutionLayer
    authority: AuthorityClass
    language: LanguageAxis
    dataset_id: str


def is_regression_harness(dataset_id: str) -> bool:
    """Return True when the dataset refers to the internal regression harness."""

    return dataset_id == REGRESSION_HARNESS_DATASET_ID


def get_dataset_authority(dataset_id: str) -> AuthorityClass:
    """Resolve the supported runtime authority for a dataset ID."""

    if is_regression_harness(dataset_id):
        return "regression_harness"
    if is_official(dataset_id):
        return "official_suite"
    raise ValueError(f"unsupported benchmark dataset: {dataset_id}")


def get_layer_policy(layer: ExecutionLayer | str) -> dict[str, object]:
    """Return the default configuration for an execution layer."""

    return get_execution_layer_policy(layer).to_dict()


def is_local_diagnostic(dataset_id: str) -> bool:
    """Compatibility helper for the internal regression harness downgrade."""

    return is_regression_harness(dataset_id)


def resolve_policy(
    layer: ExecutionLayer | str,
    dataset_id: str,
) -> BenchmarkPolicy:
    """Resolve the full policy for a layer + dataset combination."""

    authority = get_dataset_authority(dataset_id)
    entry = get_dataset_entry(dataset_id)
    language = entry.language_axis if entry else "multilingual"
    return BenchmarkPolicy(
        layer=canonicalize_execution_layer(layer),
        authority=authority,
        language=language,
        dataset_id=dataset_id,
    )


def get_quick_pr_suite() -> tuple[str, ...]:
    """Return the official quick PR suite dataset IDs."""

    return official_suite_dataset_ids()


def get_scheduled_suite() -> tuple[str, ...]:
    """Return the full official scheduled suite dataset IDs."""

    return official_suite_dataset_ids()
