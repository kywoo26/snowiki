from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, cast

from snowiki.bench.contract import PHASE_1_CORPUS
from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.query import run_query
from snowiki.cli.commands.rebuild import run_rebuild

from .corpus import canonical_benchmark_fixtures
from .latency import summarize_latencies
from .presets import BenchmarkPreset

PHASE_1_WARMUPS = 1
PHASE_1_REPETITIONS = 5
PHASE_1_QUERY_MODE = "lexical"

_REPO_ROOT = Path(__file__).resolve().parents[2]


class FixtureSpec(TypedDict):
    source: str
    path: Path


def _load_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _canonical_fixtures() -> tuple[FixtureSpec, ...]:
    fixtures: list[FixtureSpec] = []
    for fixture in canonical_benchmark_fixtures():
        fixtures.append({"source": fixture.source, "path": fixture.path})
    return tuple(fixtures)


def _load_queries_for_preset(preset: BenchmarkPreset) -> tuple[str, ...]:
    payload = _load_json(_REPO_ROOT / PHASE_1_CORPUS["queries"])
    rows = cast(list[dict[str, object]], payload["queries"])
    return tuple(
        str(row["text"])
        for row in rows
        if str(row.get("kind", "known-item")) in preset.query_kinds
    )


def _fixture_report_path(path: Path) -> str:
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _run_ingest_flow(root: Path) -> None:
    for fixture in _canonical_fixtures():
        _ = run_ingest(fixture["path"], source=fixture["source"], root=root)


def _run_rebuild_flow(root: Path) -> None:
    _run_ingest_flow(root)
    _ = run_rebuild(root)


def _run_query_flow(root: Path, *, queries: tuple[str, ...], top_k: int) -> None:
    _run_rebuild_flow(root)
    for query_text in queries:
        _ = run_query(root, query_text, mode=PHASE_1_QUERY_MODE, top_k=top_k)


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


def run_phase1_latency_evaluation(
    root: Path,
    *,
    preset: BenchmarkPreset,
) -> dict[str, object]:
    fixtures = _canonical_fixtures()
    queries = _load_queries_for_preset(preset)
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
                warmups=PHASE_1_WARMUPS,
                repetitions=PHASE_1_REPETITIONS,
                callback=_run_ingest_flow,
            ),
            "rebuild": _measure_flow(
                "rebuild",
                parent_root=base_root,
                warmups=PHASE_1_WARMUPS,
                repetitions=PHASE_1_REPETITIONS,
                callback=_run_rebuild_flow,
            ),
            "query": _measure_flow(
                "query",
                parent_root=base_root,
                warmups=PHASE_1_WARMUPS,
                repetitions=PHASE_1_REPETITIONS,
                callback=run_query_iteration,
            ),
        }

    return {
        "corpus": {
            "queries_path": PHASE_1_CORPUS["queries"],
            "judgments_path": PHASE_1_CORPUS["judgments"],
            "fixtures": [
                {
                    "source": fixture["source"],
                    "path": _fixture_report_path(fixture["path"]),
                }
                for fixture in fixtures
            ],
            "fixtures_indexed": len(fixtures),
            "queries_evaluated": len(queries),
        },
        "protocol": {
            "isolated_root": True,
            "warmups": PHASE_1_WARMUPS,
            "repetitions": PHASE_1_REPETITIONS,
            "query_mode": PHASE_1_QUERY_MODE,
            "top_k": preset.top_k,
        },
        "performance": performance,
    }
