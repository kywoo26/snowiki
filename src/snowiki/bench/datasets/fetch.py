from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from huggingface_hub import snapshot_download

from snowiki.config import get_benchmark_data_root

from .cache import (
    BenchmarkDatasetCacheMissingError,
    get_benchmark_dataset_lock_path,
    get_benchmark_hf_cache_root,
    resolve_cached_benchmark_dataset,
    write_benchmark_dataset_lock,
)
from .registry import get_benchmark_dataset_spec
from .specs import (
    BenchmarkDatasetFetchResult,
    BenchmarkDatasetId,
    BenchmarkDatasetSourceFetch,
    BenchmarkDatasetSourceSpec,
    RefreshMode,
)


def fetch_benchmark_dataset(
    dataset_id: BenchmarkDatasetId,
    *,
    data_root: Path | None = None,
    refresh: RefreshMode = "if-missing",
    local_files_only: bool = False,
    revision: str | None = None,
) -> BenchmarkDatasetFetchResult:
    """Fetch a benchmark dataset into the benchmark-owned cache."""

    benchmark_data_root = get_benchmark_data_root(data_root)
    spec = get_benchmark_dataset_spec(dataset_id)
    lock_path = get_benchmark_dataset_lock_path(dataset_id, benchmark_data_root)

    if refresh == "if-missing":
        try:
            cached_result = resolve_cached_benchmark_dataset(
                dataset_id,
                data_root=benchmark_data_root,
            )
        except BenchmarkDatasetCacheMissingError:
            cached_result = None
        if cached_result is not None and _cached_revisions_match(
            cached_result=cached_result,
            expected_sources=spec.sources,
            revision=revision,
        ):
            return cached_result

    cache_root = get_benchmark_hf_cache_root(benchmark_data_root)
    fetched_sources: list[BenchmarkDatasetSourceFetch] = []
    with _benchmark_hf_home(cache_root):
        for source in spec.sources:
            requested_revision = revision or source.default_revision
            snapshot_path = _download_snapshot(
                source=source,
                requested_revision=requested_revision,
                cache_root=cache_root,
                local_files_only=local_files_only,
                refresh=refresh,
            )
            fetched_sources.append(
                BenchmarkDatasetSourceFetch(
                    label=source.label,
                    name=source.name,
                    repo_id=source.repo_id,
                    repo_type=source.repo_type,
                    requested_revision=requested_revision,
                    snapshot_path=snapshot_path,
                    allow_patterns=source.allow_patterns,
                )
            )

    _ = write_benchmark_dataset_lock(
        lock_path=lock_path,
        spec=spec,
        fetched_sources=tuple(fetched_sources),
    )
    return BenchmarkDatasetFetchResult(
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        sources=tuple(fetched_sources),
        lock_path=lock_path,
    )


def _cached_revisions_match(
    *,
    cached_result: BenchmarkDatasetFetchResult,
    expected_sources: tuple[BenchmarkDatasetSourceSpec, ...],
    revision: str | None,
) -> bool:
    if revision is None:
        expected_revisions = tuple(source.default_revision for source in expected_sources)
    else:
        expected_revisions = tuple(revision for _ in expected_sources)
    actual_revisions = tuple(source.requested_revision for source in cached_result.sources)
    return actual_revisions == expected_revisions


def _download_snapshot(
    *,
    source: BenchmarkDatasetSourceSpec,
    requested_revision: str,
    cache_root: Path,
    local_files_only: bool,
    refresh: RefreshMode,
) -> Path:
    snapshot_location = snapshot_download(
        repo_id=source.repo_id,
        repo_type=source.repo_type,
        revision=requested_revision,
        allow_patterns=list(source.allow_patterns),
        cache_dir=cache_root,
        local_files_only=local_files_only,
        force_download=refresh == "force",
    )
    snapshot_path = Path(snapshot_location).resolve()
    snapshot_path.mkdir(parents=True, exist_ok=True)
    return snapshot_path


@contextmanager
def _benchmark_hf_home(cache_root: Path) -> Iterator[None]:
    previous_hf_home = os.environ.get("HF_HOME")
    os.environ["HF_HOME"] = cache_root.as_posix()
    try:
        yield
    finally:
        if previous_hf_home is None:
            _ = os.environ.pop("HF_HOME", None)
        else:
            os.environ["HF_HOME"] = previous_hf_home


__all__ = ["fetch_benchmark_dataset"]
