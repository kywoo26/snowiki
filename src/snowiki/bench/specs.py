from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LevelConfig:
    """One named evaluation level from the matrix contract."""

    level_id: str
    query_cap: int
    corpus_cap: int | None = None
    note: str | None = None


@dataclass(frozen=True)
class EvaluationMatrix:
    """A thin input contract describing datasets and evaluation levels."""

    matrix_id: str
    datasets: tuple[str, ...]
    levels: dict[str, LevelConfig]


@dataclass(frozen=True)
class DatasetManifest:
    """Metadata-only manifest describing one benchmark dataset."""

    dataset_id: str
    name: str
    language: str
    purpose_tags: tuple[str, ...]
    corpus_path: str
    queries_path: str
    judgments_path: str
    field_mappings: dict[str, tuple[str, ...]]
    supported_levels: tuple[str, ...]
    source: dict[str, DatasetSourceLocator] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetSourceLocator:
    """Pinned upstream locator for one dataset asset."""

    repo_id: str
    config: str
    split: str
    revision: str
    loader: str | None = None
    data_files: tuple[str, ...] = ()
    load_kwargs: dict[str, object] = field(default_factory=dict)
    trust_remote_code: bool = False


@dataclass(frozen=True)
class BenchmarkTargetSpec:
    """Registered metadata for one retrieval target adapter."""

    target_id: str
    description: str | None = None
    supported_datasets: tuple[str, ...] = ()
    supported_levels: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryResult:
    """Normalized retrieval output for one query execution."""

    query_id: str
    ranked_doc_ids: tuple[str, ...]
    latency_ms: float | None = None


@dataclass(frozen=True)
class BenchmarkQuery:
    """One materialized benchmark query selected by the runner."""

    query_id: str
    query_text: str


class RetrievalTargetAdapter(Protocol):
    """Execution seam used by the lean benchmark runner."""

    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class MetricResult:
    """One computed metric value for a cell result."""

    metric_id: str
    value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CellResult:
    """One matrix cell outcome for dataset, level, and target."""

    dataset_id: str
    level_id: str
    target_id: str
    metrics: tuple[MetricResult, ...] = ()
    status: str = "not_run"
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkRunResult:
    """Aggregate output for one matrix execution attempt."""

    matrix_id: str
    cells: tuple[CellResult, ...] = ()
    failures: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)
