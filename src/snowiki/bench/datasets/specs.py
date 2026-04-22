from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

BenchmarkDatasetId = Literal[
    "ms_marco_passage",
    "trec_dl_2020_passage",
    "miracl_ko",
    "miracl_en",
    "beir_nq",
    "beir_scifact",
]
RefreshMode = Literal["if-missing", "force"]


@dataclass(frozen=True)
class BenchmarkDatasetSourceSpec:
    """Remote source needed to materialize a logical benchmark dataset."""

    label: str
    name: str
    repo_id: str
    repo_type: Literal["dataset"]
    default_revision: str
    allow_patterns: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkDatasetSpec:
    """Registry entry for a downloadable benchmark dataset."""

    dataset_id: BenchmarkDatasetId
    language: str
    tier: Literal["official_suite"]
    citation: str
    license: str
    source_url: str
    sources: tuple[BenchmarkDatasetSourceSpec, ...]


@dataclass(frozen=True)
class BenchmarkDatasetSourceFetch:
    """Materialized fetch metadata for one source in a benchmark dataset."""

    label: str
    name: str
    repo_id: str
    repo_type: Literal["dataset"]
    requested_revision: str
    snapshot_path: Path
    allow_patterns: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkDatasetFetchResult:
    """Materialized fetch metadata for a benchmark dataset."""

    dataset_id: BenchmarkDatasetId
    benchmark_data_root: Path
    sources: tuple[BenchmarkDatasetSourceFetch, ...]
    lock_path: Path

    @property
    def snapshot_path(self) -> Path:
        """Return the first source snapshot path for legacy callers."""

        return self.sources[0].snapshot_path

    @property
    def requested_revision(self) -> str:
        """Return the first requested revision for legacy callers."""

        return self.sources[0].requested_revision


__all__ = [
    "BenchmarkDatasetFetchResult",
    "BenchmarkDatasetId",
    "BenchmarkDatasetSourceFetch",
    "BenchmarkDatasetSourceSpec",
    "BenchmarkDatasetSpec",
    "RefreshMode",
]
