"""Official benchmark catalog for the lean six-dataset suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

LanguageAxis = Literal["en", "ko", "multilingual"]


@dataclass(frozen=True)
class OfficialDatasetEntry:
    """A single dataset in the supported official benchmark suite."""

    dataset_id: str
    name: str
    language_axis: LanguageAxis
    description: str
    source_url: str

    @property
    def authority_class(self) -> Literal["official_suite"]:
        """Return the collapsed runtime authority for official datasets."""

        return "official_suite"


OFFICIAL_BENCHMARK_SUITE: Final[tuple[OfficialDatasetEntry, ...]] = (
    OfficialDatasetEntry(
        dataset_id="ms_marco_passage",
        name="MS MARCO Passage Ranking",
        language_axis="en",
        description="Classic passage-retrieval benchmark from Bing logs.",
        source_url="https://github.com/microsoft/MSMARCO-Passage-Ranking",
    ),
    OfficialDatasetEntry(
        dataset_id="trec_dl_2020_passage",
        name="TREC DL 2020 Passage",
        language_axis="en",
        description="NIST judged passage ranking track on MS MARCO.",
        source_url="https://microsoft.github.io/msmarco/TREC-Deep-Learning-2020",
    ),
    OfficialDatasetEntry(
        dataset_id="miracl_ko",
        name="MIRACL Korean",
        language_axis="ko",
        description="Multilingual IR benchmark — Korean slice.",
        source_url="https://github.com/project-miracl/miracl",
    ),
    OfficialDatasetEntry(
        dataset_id="miracl_en",
        name="MIRACL English",
        language_axis="en",
        description="Multilingual IR benchmark — English slice.",
        source_url="https://github.com/project-miracl/miracl",
    ),
    OfficialDatasetEntry(
        dataset_id="beir_nq",
        name="BEIR Natural Questions",
        language_axis="en",
        description="BEIR zero-shot retrieval — Natural Questions.",
        source_url="https://github.com/beir-cellar/beir",
    ),
    OfficialDatasetEntry(
        dataset_id="beir_scifact",
        name="BEIR SciFact",
        language_axis="en",
        description="BEIR zero-shot retrieval — scientific claim verification.",
        source_url="https://github.com/beir-cellar/beir",
    ),
)

OFFICIAL_BALANCED_CORE: Final[tuple[OfficialDatasetEntry, ...]] = OFFICIAL_BENCHMARK_SUITE

_DATASET_BY_ID: Final[dict[str, OfficialDatasetEntry]] = {
    entry.dataset_id: entry for entry in OFFICIAL_BENCHMARK_SUITE
}


def get_dataset_entry(dataset_id: str) -> OfficialDatasetEntry | None:
    """Return the official catalog entry for a dataset ID."""

    return _DATASET_BY_ID.get(dataset_id)


def is_official(dataset_id: str) -> bool:
    """Return True when the dataset is part of the official six-dataset suite."""

    return dataset_id in _DATASET_BY_ID


def get_official_datasets_by_language(
    language: LanguageAxis,
) -> tuple[OfficialDatasetEntry, ...]:
    """Return official datasets matching the requested language axis."""

    return tuple(
        entry for entry in OFFICIAL_BENCHMARK_SUITE if entry.language_axis == language
    )


def official_suite_dataset_ids() -> tuple[str, ...]:
    """Return the canonical official suite ordering."""

    return tuple(entry.dataset_id for entry in OFFICIAL_BENCHMARK_SUITE)
