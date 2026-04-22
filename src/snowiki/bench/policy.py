"""Official benchmark policy contract.

Separates execution layers from evidence authority classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

ExecutionLayer = Literal["pr_official_quick", "scheduled_official_broad", "release_proof"]
AuthorityClass = Literal["official_standard", "official_candidate", "local_diagnostic"]
LanguageAxis = Literal["en", "ko", "multilingual"]


@dataclass(frozen=True)
class OfficialDatasetEntry:
    """A single entry in the official benchmark registry."""

    dataset_id: str
    name: str
    authority_class: AuthorityClass
    language_axis: LanguageAxis
    description: str
    source_url: str


@dataclass(frozen=True)
class BenchmarkPolicy:
    """Resolved policy for a benchmark run."""

    layer: ExecutionLayer
    authority: AuthorityClass
    language: LanguageAxis
    dataset_id: str


# Ordered by priority / standardness
OFFICIAL_BALANCED_CORE: Final[tuple[OfficialDatasetEntry, ...]] = (
    OfficialDatasetEntry(
        dataset_id="ms_marco_passage",
        name="MS MARCO Passage Ranking",
        authority_class="official_standard",
        language_axis="en",
        description="Classic passage-retrieval benchmark from Bing logs.",
        source_url="https://github.com/microsoft/MSMARCO-Passage-Ranking",
    ),
    OfficialDatasetEntry(
        dataset_id="trec_dl_2020_passage",
        name="TREC DL 2020 Passage",
        authority_class="official_standard",
        language_axis="en",
        description="NIST judged passage ranking track on MS MARCO.",
        source_url="https://microsoft.github.io/msmarco/TREC-Deep-Learning-2020",
    ),
    OfficialDatasetEntry(
        dataset_id="miracl_ko",
        name="MIRACL Korean",
        authority_class="official_standard",
        language_axis="ko",
        description="Multilingual IR benchmark — Korean slice.",
        source_url="https://github.com/project-miracl/miracl",
    ),
    OfficialDatasetEntry(
        dataset_id="miracl_en",
        name="MIRACL English",
        authority_class="official_standard",
        language_axis="en",
        description="Multilingual IR benchmark — English slice.",
        source_url="https://github.com/project-miracl/miracl",
    ),
    OfficialDatasetEntry(
        dataset_id="beir_nq",
        name="BEIR Natural Questions",
        authority_class="official_standard",
        language_axis="en",
        description="BEIR zero-shot retrieval — Natural Questions.",
        source_url="https://github.com/beir-cellar/beir",
    ),
    OfficialDatasetEntry(
        dataset_id="beir_scifact",
        name="BEIR SciFact",
        authority_class="official_standard",
        language_axis="en",
        description="BEIR zero-shot retrieval — scientific claim verification.",
        source_url="https://github.com/beir-cellar/beir",
    ),
)

# Quick lookup maps
_DATASET_BY_ID: Final[dict[str, OfficialDatasetEntry]] = {
    d.dataset_id: d for d in OFFICIAL_BALANCED_CORE
}

# Layer configurations
_LAYER_DEFAULTS: Final[dict[ExecutionLayer, dict[str, object]]] = {
    "pr_official_quick": {
        "sample_mode": "quick",
        "metrics": ("nDCG@10", "Recall@100", "MRR@10", "P95 latency"),
        "blocking": True,
    },
    "scheduled_official_broad": {
        "sample_mode": "standard",
        "metrics": ("nDCG@10", "Recall@100", "MRR@10", "P95 latency"),
        "blocking": False,
    },
    "release_proof": {
        "sample_mode": "full",
        "metrics": ("nDCG@10", "Recall@100", "MRR@10", "P95 latency"),
        "blocking": True,
        "enabled_by_default": False,
    },
}

# Local diagnostic datasets (NOT official)
_LOCAL_DIAGNOSTIC_DATASETS: Final[frozenset[str]] = frozenset({
    "regression",
    "snowiki_shaped",
    "hidden_holdout",
})


def get_dataset_entry(dataset_id: str) -> OfficialDatasetEntry | None:
    """Return the official registry entry for a dataset, or None if not official."""
    return _DATASET_BY_ID.get(dataset_id)


def get_dataset_authority(dataset_id: str) -> AuthorityClass:
    """Resolve the authority class for a dataset ID."""
    if dataset_id in _LOCAL_DIAGNOSTIC_DATASETS:
        return "local_diagnostic"
    entry = get_dataset_entry(dataset_id)
    if entry is not None:
        return entry.authority_class
    # Unknown datasets default to candidate until reviewed
    return "official_candidate"


def get_layer_policy(layer: ExecutionLayer) -> dict[str, object]:
    """Return the default configuration for an execution layer."""
    return dict(_LAYER_DEFAULTS[layer])


def is_official(dataset_id: str) -> bool:
    """Return True if the dataset is part of the official benchmark registry."""
    return dataset_id in _DATASET_BY_ID


def is_local_diagnostic(dataset_id: str) -> bool:
    """Return True if the dataset is a local diagnostic suite."""
    return dataset_id in _LOCAL_DIAGNOSTIC_DATASETS


def resolve_policy(
    layer: ExecutionLayer,
    dataset_id: str,
) -> BenchmarkPolicy:
    """Resolve the full policy for a layer + dataset combination."""
    authority = get_dataset_authority(dataset_id)
    entry = get_dataset_entry(dataset_id)
    language = entry.language_axis if entry else "multilingual"
    return BenchmarkPolicy(
        layer=layer,
        authority=authority,
        language=language,
        dataset_id=dataset_id,
    )


def get_official_datasets_by_language(
    language: LanguageAxis,
) -> tuple[OfficialDatasetEntry, ...]:
    """Return all official datasets for a given language axis."""
    return tuple(d for d in OFFICIAL_BALANCED_CORE if d.language_axis == language)


def get_quick_pr_suite() -> tuple[str, ...]:
    """Return the official quick PR suite dataset IDs."""
    return tuple(d.dataset_id for d in OFFICIAL_BALANCED_CORE)


def get_scheduled_suite() -> tuple[str, ...]:
    """Return the full official scheduled suite dataset IDs."""
    return tuple(d.dataset_id for d in OFFICIAL_BALANCED_CORE)
