from __future__ import annotations

from pathlib import Path
from typing import cast

from snowiki.config import get_benchmark_data_root
from snowiki.storage.zones import atomic_write_json, isoformat_utc, read_json

from .registry import get_benchmark_dataset_spec
from .specs import (
    BenchmarkDatasetFetchResult,
    BenchmarkDatasetId,
    BenchmarkDatasetSourceFetch,
    BenchmarkDatasetSourceSpec,
    BenchmarkDatasetSpec,
)


class BenchmarkDatasetCacheMissingError(RuntimeError):
    """Raised when a cached benchmark dataset cannot be reopened."""


def get_benchmark_hf_cache_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned Hugging Face cache root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "hf")


def get_benchmark_locks_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned lock metadata root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "locks")


def get_benchmark_materialized_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned materialized data root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "materialized")


def get_benchmark_downloads_root(root: Path | None = None) -> Path:
    """Return the benchmark-owned downloads root."""

    return _ensure_subdirectory(get_benchmark_data_root(root), "downloads")


def get_benchmark_dataset_lock_path(
    dataset_id: BenchmarkDatasetId, root: Path | None = None
) -> Path:
    """Return the lock metadata path for a benchmark dataset."""

    return get_benchmark_locks_root(root) / f"{dataset_id}.json"


def resolve_cached_benchmark_dataset(
    dataset_id: BenchmarkDatasetId, *, data_root: Path | None = None
) -> BenchmarkDatasetFetchResult:
    """Reopen a previously fetched benchmark dataset from lock metadata."""

    benchmark_data_root = get_benchmark_data_root(data_root)
    spec = get_benchmark_dataset_spec(dataset_id)
    lock_path = get_benchmark_dataset_lock_path(dataset_id, benchmark_data_root)
    cached_result = _load_cached_fetch(
        lock_path=lock_path,
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        spec=spec,
    )
    if cached_result is None:
        raise BenchmarkDatasetCacheMissingError(
            _missing_cache_message(dataset_id=dataset_id, benchmark_data_root=benchmark_data_root)
        )
    return cached_result


def write_benchmark_dataset_lock(
    *,
    lock_path: Path,
    spec: BenchmarkDatasetSpec,
    fetched_sources: tuple[BenchmarkDatasetSourceFetch, ...],
) -> Path:
    payload = {
        "dataset_id": spec.dataset_id,
        "fetched_at": isoformat_utc(None),
        "language": spec.language,
        "tier": spec.tier,
        "source_url": spec.source_url,
        "citation": spec.citation,
        "license": spec.license,
        "sources": [
            {
                "label": source.label,
                "name": source.name,
                "repo_id": source.repo_id,
                "repo_type": source.repo_type,
                "requested_revision": source.requested_revision,
                "resolved_snapshot_path": source.snapshot_path.as_posix(),
                "allow_patterns": list(source.allow_patterns),
            }
            for source in fetched_sources
        ],
    }
    return atomic_write_json(lock_path, payload)


def _missing_cache_message(
    *, dataset_id: BenchmarkDatasetId, benchmark_data_root: Path
) -> str:
    return (
        f"benchmark dataset '{dataset_id}' is not cached under "
        f"{benchmark_data_root.as_posix()}; run `uv run snowiki benchmark-fetch "
        f"--dataset {dataset_id}` first"
    )


def _ensure_subdirectory(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_cached_fetch(
    *,
    lock_path: Path,
    dataset_id: BenchmarkDatasetId,
    benchmark_data_root: Path,
    spec: BenchmarkDatasetSpec,
) -> BenchmarkDatasetFetchResult | None:
    payload_raw = cast(object, read_json(lock_path, None))
    if not isinstance(payload_raw, dict):
        return None
    payload = cast(dict[str, object], payload_raw)
    if payload.get("dataset_id") != dataset_id:
        return None
    fetched_sources = _load_locked_sources(payload, spec=spec)
    if fetched_sources is None:
        return None
    return BenchmarkDatasetFetchResult(
        dataset_id=dataset_id,
        benchmark_data_root=benchmark_data_root,
        sources=fetched_sources,
        lock_path=lock_path,
    )


def _load_locked_sources(
    payload: dict[str, object], *, spec: BenchmarkDatasetSpec
) -> tuple[BenchmarkDatasetSourceFetch, ...] | None:
    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or len(sources_raw) != len(spec.sources):
        return None

    fetched_sources: list[BenchmarkDatasetSourceFetch] = []
    for expected_source, source_raw in zip(spec.sources, sources_raw, strict=True):
        if not isinstance(source_raw, dict):
            return None
        source_payload = cast(dict[str, object], source_raw)
        if not _locked_source_matches(source_payload, source=expected_source):
            return None
        requested_revision = source_payload.get("requested_revision")
        snapshot_value = source_payload.get("resolved_snapshot_path")
        if not isinstance(requested_revision, str) or not requested_revision.strip():
            return None
        if not isinstance(snapshot_value, str) or not snapshot_value.strip():
            return None
        snapshot_path = Path(snapshot_value)
        if not snapshot_path.exists():
            return None
        fetched_sources.append(
            BenchmarkDatasetSourceFetch(
                label=expected_source.label,
                name=expected_source.name,
                repo_id=expected_source.repo_id,
                repo_type=expected_source.repo_type,
                requested_revision=requested_revision,
                snapshot_path=snapshot_path,
                allow_patterns=expected_source.allow_patterns,
            )
        )
    return tuple(fetched_sources)


def _locked_source_matches(
    payload: dict[str, object], *, source: BenchmarkDatasetSourceSpec
) -> bool:
    return (
        payload.get("label") == source.label
        and payload.get("name") == source.name
        and payload.get("repo_id") == source.repo_id
        and payload.get("repo_type") == source.repo_type
        and payload.get("allow_patterns") == list(source.allow_patterns)
    )


__all__ = [
    "BenchmarkDatasetCacheMissingError",
    "BenchmarkDatasetFetchResult",
    "BenchmarkDatasetId",
    "get_benchmark_dataset_lock_path",
    "get_benchmark_downloads_root",
    "get_benchmark_hf_cache_root",
    "get_benchmark_locks_root",
    "get_benchmark_materialized_root",
    "resolve_cached_benchmark_dataset",
]
