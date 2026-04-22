"""Latency benchmarking helpers.

This module measures ingest, rebuild, and query latency using the canonical
benchmark corpus and configured presets.
"""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.query import run_query
from snowiki.cli.commands.rebuild import run_rebuild
from snowiki.config import get_repo_root, resolve_repo_asset_path
from snowiki.storage.zones import relative_to_root_or_posix

from ..contract import BENCHMARK_CORPUS
from ..contract.presets import BenchmarkPreset
from ..runtime.corpus import BenchmarkCorpusManifest, canonical_benchmark_fixtures
from ..runtime.latency import summarize_latencies

BENCHMARK_WARMUPS = 1
BENCHMARK_REPETITIONS = 5
BENCHMARK_QUERY_MODE = "lexical"
BENCHMARK_FIXED_SAMPLE_SIZE = 20
BENCHMARK_STRATIFIED_SAMPLE_SIZE = 20


class FixtureSpec(TypedDict):
    """Specification for a benchmark fixture used in latency runs.

    Attributes:
        source: Source system label for the fixture.
        path: Filesystem path to the fixture file.
    """

    source: str
    path: Path


class QuerySpec(TypedDict):
    """Specification for a benchmark query used in latency runs."""

    text: str
    kind: str
    id: NotRequired[str]
    group: NotRequired[str]
    tags: NotRequired[list[str]]


@dataclass(frozen=True)
class LatencySamplingPolicy:
    """Configuration for tier-aware latency query sampling."""

    mode: Literal["exhaustive", "stratified", "fixed_sample"]
    sample_size: int | None = None
    strata: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"mode": self.mode}
        if self.sample_size is not None:
            payload["sample_size"] = self.sample_size
        if self.strata is not None:
            payload["strata"] = list(self.strata)
        return payload


def _load_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _canonical_fixtures() -> tuple[FixtureSpec, ...]:
    fixtures: list[FixtureSpec] = []
    for fixture in canonical_benchmark_fixtures():
        fixtures.append({"source": fixture.source, "path": fixture.path})
    return tuple(fixtures)


def _query_specs_from_rows(
    rows: list[dict[str, object]], *, preset: BenchmarkPreset
) -> tuple[QuerySpec, ...]:
    queries: list[QuerySpec] = []
    for row in rows:
        kind = str(row.get("kind", "known-item"))
        if kind not in preset.query_kinds:
            continue
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        query: QuerySpec = {"text": text, "kind": kind}
        query_id = str(row.get("id", "")).strip()
        if query_id:
            query["id"] = query_id
        group = str(row.get("group", "")).strip()
        if group:
            query["group"] = group
        raw_tags = row.get("tags")
        if isinstance(raw_tags, list):
            tags = [str(tag) for tag in raw_tags if str(tag).strip()]
            if tags:
                query["tags"] = tags
        queries.append(query)
    return tuple(queries)


def _load_query_specs_for_preset(
    preset: BenchmarkPreset,
    *,
    manifest: BenchmarkCorpusManifest | None = None,
) -> tuple[QuerySpec, ...]:
    if manifest is not None and manifest.queries is not None:
        return _query_specs_from_rows(manifest.queries, preset=preset)

    payload = _load_json(resolve_repo_asset_path(BENCHMARK_CORPUS["queries"]))
    rows = cast(list[dict[str, object]], payload["queries"])
    return _query_specs_from_rows(rows, preset=preset)


def get_latency_policy(tier: str, query_count: int) -> LatencySamplingPolicy:
    """Resolve the default latency sampling policy for a dataset tier."""

    if tier == "official_suite" and query_count > 50:
        return LatencySamplingPolicy(mode="stratified")
    return LatencySamplingPolicy(mode="exhaustive")


def _requested_latency_policy(
    tier: str,
    *,
    query_count: int,
    latency_sample: Literal["exhaustive", "stratified", "fixed_sample"] | None,
) -> LatencySamplingPolicy:
    if latency_sample is None:
        return get_latency_policy(tier, query_count)
    if latency_sample == "fixed_sample":
        return LatencySamplingPolicy(
            mode="fixed_sample",
            sample_size=min(BENCHMARK_FIXED_SAMPLE_SIZE, query_count),
        )
    if latency_sample == "stratified":
        return LatencySamplingPolicy(mode="stratified")
    return LatencySamplingPolicy(mode="exhaustive")


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _derive_latency_strata(queries: tuple[QuerySpec, ...]) -> list[str]:
    groups = _ordered_unique([str(query.get("group", "")) for query in queries])
    if len(groups) > 1:
        return groups

    kinds = _ordered_unique([str(query.get("kind", "")) for query in queries])
    if len(kinds) > 1:
        return kinds

    if groups:
        return groups
    if kinds:
        return kinds
    return ["all"]


def _materialize_latency_policy(
    policy: LatencySamplingPolicy,
    *,
    queries: tuple[QuerySpec, ...],
) -> LatencySamplingPolicy:
    if policy.mode != "stratified" or policy.strata:
        return policy
    return replace(policy, strata=_derive_latency_strata(queries))


def _query_matches_stratum(query: QuerySpec, stratum: str) -> bool:
    return str(query.get("group", "")) == stratum or str(query.get("kind", "")) == stratum


def _evenly_spaced_positions(length: int, sample_size: int) -> list[int]:
    if sample_size <= 0 or length <= 0:
        return []
    if sample_size >= length:
        return list(range(length))
    return [((2 * index + 1) * length) // (2 * sample_size) for index in range(sample_size)]


def _fixed_sample_query_positions(length: int, sample_size: int) -> list[int]:
    return _evenly_spaced_positions(length, min(sample_size, length))


def _stratified_sample_query_positions(
    queries: tuple[QuerySpec, ...],
    *,
    strata: list[str],
) -> list[int]:
    if not queries:
        return []

    target = min(BENCHMARK_STRATIFIED_SAMPLE_SIZE, len(queries))
    if target <= 0:
        return []
    if not strata:
        return _fixed_sample_query_positions(len(queries), target)

    buckets: dict[str, list[int]] = {stratum: [] for stratum in strata}
    unmatched: list[int] = []
    for index, query in enumerate(queries):
        matched = False
        for stratum in strata:
            if _query_matches_stratum(query, stratum):
                buckets[stratum].append(index)
                matched = True
                break
        if not matched:
            unmatched.append(index)

    active_strata = [stratum for stratum in strata if buckets[stratum]]
    if not active_strata:
        return _fixed_sample_query_positions(len(queries), target)

    quotas = dict.fromkeys(active_strata, 0)
    remaining = target
    for stratum in active_strata:
        if remaining == 0:
            break
        quotas[stratum] = 1
        remaining -= 1

    while remaining > 0:
        progressed = False
        for stratum in active_strata:
            if remaining == 0:
                break
            if quotas[stratum] >= len(buckets[stratum]):
                continue
            quotas[stratum] += 1
            remaining -= 1
            progressed = True
        if not progressed:
            break

    selected: set[int] = set()
    for stratum in active_strata:
        bucket = buckets[stratum]
        for position in _evenly_spaced_positions(len(bucket), quotas[stratum]):
            selected.add(bucket[position])

    if remaining > 0:
        remainder_pool = [
            index
            for index in [*unmatched, *range(len(queries))]
            if index not in selected
        ]
        unique_pool = list(dict.fromkeys(remainder_pool))
        for position in _evenly_spaced_positions(len(unique_pool), remaining):
            selected.add(unique_pool[position])

    return sorted(selected)


def _sampled_queries(
    queries: tuple[QuerySpec, ...],
    *,
    policy: LatencySamplingPolicy,
) -> tuple[tuple[QuerySpec, ...], LatencySamplingPolicy]:
    materialized_policy = _materialize_latency_policy(policy, queries=queries)
    if materialized_policy.mode == "exhaustive":
        return queries, materialized_policy
    if materialized_policy.mode == "fixed_sample":
        positions = _fixed_sample_query_positions(
            len(queries), materialized_policy.sample_size or BENCHMARK_FIXED_SAMPLE_SIZE
        )
        return tuple(queries[position] for position in positions), materialized_policy
    positions = _stratified_sample_query_positions(
        queries,
        strata=materialized_policy.strata or [],
    )
    return tuple(queries[position] for position in positions), materialized_policy


def _sampling_policy_payload(
    policy: LatencySamplingPolicy,
    *,
    population_query_count: int,
    sampled_query_count: int,
) -> dict[str, object]:
    return {
        **policy.to_dict(),
        "population_query_count": population_query_count,
        "sampled_query_count": sampled_query_count,
        "sampled": sampled_query_count != population_query_count,
    }


def _fixture_report_path(path: Path) -> str:
    return relative_to_root_or_posix(get_repo_root(), path)


def _run_ingest_flow(root: Path) -> None:
    for fixture in _canonical_fixtures():
        _ = run_ingest(fixture["path"], source=fixture["source"], root=root)


def _run_rebuild_flow(root: Path) -> None:
    _run_ingest_flow(root)
    _ = run_rebuild(root)


def _run_query_flow(root: Path, *, queries: tuple[str, ...], top_k: int) -> None:
    _run_rebuild_flow(root)
    for query_text in queries:
        _ = run_query(root, query_text, mode=BENCHMARK_QUERY_MODE, top_k=top_k)


def _measure_flow(
    flow: str,
    *,
    parent_root: Path,
    warmups: int,
    repetitions: int,
    callback: Callable[[Path], None],
) -> dict[str, float]:
    flow_root = parent_root / flow
    flow_root.mkdir(parents=True, exist_ok=True)

    for iteration in range(1, warmups + 1):
        callback(flow_root / f"warmup-{iteration:02d}")

    durations_ms: list[float] = []
    for iteration in range(1, repetitions + 1):
        isolated_root = flow_root / f"measure-{iteration:02d}"
        started_at = time.perf_counter()
        callback(isolated_root)
        durations_ms.append((time.perf_counter() - started_at) * 1000.0)
    return summarize_latencies(durations_ms).to_dict()


def run_latency_evaluation(
    root: Path,
    *,
    preset: BenchmarkPreset,
    manifest: BenchmarkCorpusManifest | None = None,
    dataset_name: str = "regression",
    latency_sample: Literal["exhaustive", "stratified", "fixed_sample"] | None = None,
) -> dict[str, object]:
    """Measure benchmark latency for ingest, rebuild, and query flows.

    Args:
        root: Workspace root as a filesystem path.
        preset: Benchmark preset controlling query selection and top-k.

    Returns:
        A JSON-serializable dictionary containing corpus, protocol, and
        performance measurements.
    """
    fixtures = _canonical_fixtures()
    dataset_tier = manifest.tier if manifest is not None else "regression_harness"
    query_specs = _load_query_specs_for_preset(preset, manifest=manifest)
    requested_policy = _requested_latency_policy(
        dataset_tier,
        query_count=len(query_specs),
        latency_sample=latency_sample,
    )
    sampled_query_specs, sampling_policy = _sampled_queries(
        query_specs,
        policy=requested_policy,
    )
    queries = tuple(query["text"] for query in sampled_query_specs)
    temp_parent = root.parent if root.parent.exists() else None

    def run_query_iteration(isolated_root: Path) -> None:
        _run_query_flow(isolated_root, queries=queries, top_k=preset.top_k)

    with tempfile.TemporaryDirectory(
        prefix="snowiki-bench-",
        dir=str(temp_parent) if temp_parent is not None else None,
    ) as temporary_root:
        base_root = Path(temporary_root)
        performance = {
            "ingest": _measure_flow(
                "ingest",
                parent_root=base_root,
                warmups=BENCHMARK_WARMUPS,
                repetitions=BENCHMARK_REPETITIONS,
                callback=_run_ingest_flow,
            ),
            "rebuild": _measure_flow(
                "rebuild",
                parent_root=base_root,
                warmups=BENCHMARK_WARMUPS,
                repetitions=BENCHMARK_REPETITIONS,
                callback=_run_rebuild_flow,
            ),
            "query": _measure_flow(
                "query",
                parent_root=base_root,
                warmups=BENCHMARK_WARMUPS,
                repetitions=BENCHMARK_REPETITIONS,
                callback=run_query_iteration,
            ),
        }

    return {
        "corpus": {
            "dataset": dataset_name,
            "tier": dataset_tier,
            "queries_path": BENCHMARK_CORPUS["queries"],
            "judgments_path": BENCHMARK_CORPUS["judgments"],
            "fixtures": [
                {
                    "source": fixture["source"],
                    "path": _fixture_report_path(fixture["path"]),
                }
                for fixture in fixtures
            ],
            "fixtures_indexed": len(fixtures),
            "queries_available": len(query_specs),
            "queries_evaluated": len(queries),
        },
        "protocol": {
            "isolated_root": True,
            "warmups": BENCHMARK_WARMUPS,
            "repetitions": BENCHMARK_REPETITIONS,
            "query_mode": BENCHMARK_QUERY_MODE,
            "top_k": preset.top_k,
            "top_ks": list(preset.top_ks),
            "sampling_policy": _sampling_policy_payload(
                sampling_policy,
                population_query_count=len(query_specs),
                sampled_query_count=len(queries),
            ),
            **({"dataset_mode": "manifest"} if manifest is not None else {}),
        },
        "performance": performance,
    }
