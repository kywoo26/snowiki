from __future__ import annotations

import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest
from datasets import Dataset

from snowiki.bench.cache import (
    BM25_CACHE_SCHEMA_VERSION,
    build_bm25_cache_identity,
    load_or_rebuild_bm25_cache,
)
from snowiki.bench.report import render_json
from snowiki.bench.runner import (
    EXIT_CODE_INVALID_INPUT,
    EXIT_CODE_PARTIAL_FAILURE,
    EXIT_CODE_SUCCESS,
    run_cell,
    run_matrix,
    run_matrix_with_exit_code,
)
from snowiki.bench.specs import (
    BenchmarkQuery,
    BenchmarkRunResult,
    CellResult,
    DatasetManifest,
    EvaluationMatrix,
    LevelConfig,
    QueryResult,
)
from snowiki.storage.zones import StoragePaths


def test_bm25_cache_rebuilds_on_missing_manifest_and_hits_on_repeat(
    tmp_path: Path,
) -> None:
    storage_paths = StoragePaths(tmp_path / "runtime")
    identity = _cache_identity()
    builds: list[str] = []

    first = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: _built_artifact(builds, b"fresh-index"),
        load_artifact=lambda path: path.read_bytes(),
    )
    second = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: _built_artifact(builds, b"unexpected-rebuild"),
        load_artifact=lambda path: path.read_bytes(),
    )

    assert first.value == b"fresh-index"
    assert first.metadata["cache_hit"] is False
    assert first.metadata["cache_status"] == "rebuilt"
    assert first.metadata["cache_miss_reason"] == "missing_manifest"
    assert first.metadata["cache_rebuilt"] is True
    assert first.metadata["cache_schema_version"] == BM25_CACHE_SCHEMA_VERSION
    assert cast(float, first.metadata["index_build_seconds"]) >= 0.0
    assert Path(cast(str, first.metadata["cache_manifest_path"])).is_file()
    assert second.value == b"fresh-index"
    assert second.metadata["cache_hit"] is True
    assert second.metadata["cache_status"] == "hit"
    assert second.metadata["cache_miss_reason"] is None
    assert second.metadata["cache_rebuilt"] is False
    assert builds == ["built"]


@pytest.mark.parametrize(
    ("manifest_payload", "remove_artifact", "expected_reason"),
    [
        ({"schema_version": 999, "identity_hash": "different"}, False, "manifest_mismatch"),
        ("{not valid json", False, "malformed_manifest"),
        (None, True, "missing_artifact"),
    ],
)
def test_bm25_cache_rebuilds_manifest_and_artifact_failure_modes(
    tmp_path: Path,
    manifest_payload: object,
    remove_artifact: bool,
    expected_reason: str,
) -> None:
    storage_paths = StoragePaths(tmp_path / "runtime")
    identity = _cache_identity()
    seeded = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: (b"seed", b"seed"),
        load_artifact=lambda path: path.read_bytes(),
    )
    manifest_path = Path(cast(str, seeded.metadata["cache_manifest_path"]))
    artifact_path = manifest_path.with_name("index.bm25cache")
    if isinstance(manifest_payload, str):
        _ = manifest_path.write_text(manifest_payload, encoding="utf-8")
    elif manifest_payload is not None:
        _ = manifest_path.write_text(
            json.dumps(manifest_payload),
            encoding="utf-8",
        )
    if remove_artifact:
        artifact_path.unlink()
        _ = artifact_path.with_name(f".{artifact_path.name}.orphan.tmp").write_bytes(
            b"partial"
        )

    result = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: (b"rebuilt", b"rebuilt"),
        load_artifact=lambda path: path.read_bytes(),
    )

    assert result.value == b"rebuilt"
    assert result.metadata["cache_hit"] is False
    assert result.metadata["cache_status"] == "rebuilt"
    assert result.metadata["cache_miss_reason"] == expected_reason
    assert result.metadata["cache_rebuilt"] is True


def test_bm25_cache_rebuilds_when_cached_artifact_load_is_corrupt(
    tmp_path: Path,
) -> None:
    storage_paths = StoragePaths(tmp_path / "runtime")
    identity = _cache_identity()
    _ = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: (b"seed", b"seed"),
        load_artifact=lambda path: path.read_bytes(),
    )

    load_attempts = {"count": 0}

    def _load(path: Path) -> bytes:
        load_attempts["count"] += 1
        if load_attempts["count"] == 1:
            raise ValueError("cannot load cached index")
        return path.read_bytes()

    result = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: (b"rebuilt", b"rebuilt"),
        load_artifact=_load,
    )

    assert result.value == b"rebuilt"
    assert result.metadata["cache_hit"] is False
    assert result.metadata["cache_status"] == "rebuilt"
    assert result.metadata["cache_miss_reason"] == "corrupt_load"
    assert result.metadata["cache_rebuilt"] is True


def _matrix() -> EvaluationMatrix:
    return EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("dataset_a", "dataset_b"),
        levels={
            "quick": LevelConfig(level_id="quick", query_cap=10),
            "standard": LevelConfig(level_id="standard", query_cap=100),
        },
    )


def _success_cell(dataset_id: str, level_id: str, target_id: str) -> CellResult:
    return CellResult(
        dataset_id=dataset_id,
        level_id=level_id,
        target_id=target_id,
        status="success",
    )


def _manifest() -> DatasetManifest:
    return DatasetManifest(
        dataset_id="beir_nq",
        name="BEIR Natural Questions",
        language="en",
        purpose_tags=("passage-retrieval",),
        corpus_path="benchmarks/materialized/beir_nq/corpus.parquet",
        queries_path="benchmarks/materialized/beir_nq/queries.parquet",
        judgments_path="benchmarks/materialized/beir_nq/judgments.tsv",
        field_mappings={
            "query_id_keys": ("_id",),
            "query_text_keys": ("text",),
            "judgment_query_id_keys": ("query-id",),
            "judgment_doc_id_keys": ("corpus-id",),
            "judgment_relevance_keys": ("score",),
        },
        supported_levels=("quick",),
    )


def _cache_identity() -> dict[str, object]:
    return build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture/corpus.parquet",
        corpus_hash="hash",
        corpus_cap=10,
        documents=(("doc-a", "alpha"),),
        tokenizer_name="regex_v1",
        tokenizer_config={"family": "regex"},
        tokenizer_version=1,
        bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
    )


def _built_artifact(builds: list[str], content: bytes) -> tuple[bytes, bytes]:
    builds.append("built")
    return content, content


def _failed_cell(
    dataset_id: str,
    level_id: str,
    target_id: str,
    *,
    message: str,
) -> CellResult:
    return CellResult(
        dataset_id=dataset_id,
        level_id=level_id,
        target_id=target_id,
        status="failed",
        error_message=message,
    )


def test_single_cell_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, Sequence[str] | None]] = []

    def _run_cell(
        *,
        matrix: EvaluationMatrix,
        dataset_id: str,
        level_id: str,
        target_id: str,
        metric_ids: Sequence[str] | None = None,
        include_diagnostics: bool = False,
    ) -> CellResult:
        del matrix, include_diagnostics
        calls.append((dataset_id, level_id, target_id, metric_ids))
        return _success_cell(dataset_id, level_id, target_id)

    monkeypatch.setattr("snowiki.bench.runner.run_cell", _run_cell)

    result, exit_code = run_matrix_with_exit_code(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a",),
            "level_ids": ("quick",),
            "target_ids": ("bm25_regex_v1",),
        },
    )

    assert exit_code == EXIT_CODE_SUCCESS
    assert len(result.cells) == 1
    assert result.failures == ()
    assert calls == [
        (
            "dataset_a",
            "quick",
            "bm25_regex_v1",
            [
                "recall_at_1",
                "recall_at_3",
                "recall_at_5",
                "recall_at_10",
                "recall_at_100",
                "hit_rate_at_1",
                "hit_rate_at_3",
                "hit_rate_at_5",
                "hit_rate_at_10",
                "mrr_at_10",
                "ndcg_at_10",
                "latency_p50_ms",
                "latency_p95_ms",
            ],
        )
    ]
    assert run_matrix(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a",),
            "level_ids": ("quick",),
            "target_ids": ("bm25_regex_v1",),
        },
    ).cells == result.cells


def test_matrix_with_multiple_cells(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def _run_cell(
        *,
        matrix: EvaluationMatrix,
        dataset_id: str,
        level_id: str,
        target_id: str,
        metric_ids: Sequence[str] | None = None,
        include_diagnostics: bool = False,
    ) -> CellResult:
        del matrix, metric_ids, include_diagnostics
        calls.append((dataset_id, level_id, target_id))
        return _success_cell(dataset_id, level_id, target_id)

    monkeypatch.setattr("snowiki.bench.runner.run_cell", _run_cell)

    result, exit_code = run_matrix_with_exit_code(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a", "dataset_b"),
            "level_ids": ("quick", "standard"),
            "target_ids": ("bm25_regex_v1",),
        },
    )

    assert exit_code == EXIT_CODE_SUCCESS
    assert len(result.cells) == 4
    assert calls == [
        ("dataset_a", "quick", "bm25_regex_v1"),
        ("dataset_a", "standard", "bm25_regex_v1"),
        ("dataset_b", "quick", "bm25_regex_v1"),
        ("dataset_b", "standard", "bm25_regex_v1"),
    ]


def test_partial_failure_continues_when_fail_fast_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _run_cell(
        *,
        matrix: EvaluationMatrix,
        dataset_id: str,
        level_id: str,
        target_id: str,
        metric_ids: Sequence[str] | None = None,
        include_diagnostics: bool = False,
    ) -> CellResult:
        del matrix, metric_ids, include_diagnostics
        if dataset_id == "dataset_a":
            return _failed_cell(
                dataset_id,
                level_id,
                target_id,
                message="dataset_a failed",
            )
        return _success_cell(dataset_id, level_id, target_id)

    monkeypatch.setattr("snowiki.bench.runner.run_cell", _run_cell)

    result, exit_code = run_matrix_with_exit_code(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a", "dataset_b"),
            "level_ids": ("quick",),
            "target_ids": ("bm25_regex_v1",),
        },
    )

    assert exit_code == EXIT_CODE_PARTIAL_FAILURE
    assert len(result.cells) == 2
    assert [cell.status for cell in result.cells] == ["failed", "success"]
    assert result.failures == ("dataset_a failed",)


def test_fail_fast_stops_after_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def _run_cell(
        *,
        matrix: EvaluationMatrix,
        dataset_id: str,
        level_id: str,
        target_id: str,
        metric_ids: Sequence[str] | None = None,
        include_diagnostics: bool = False,
    ) -> CellResult:
        del matrix, metric_ids, include_diagnostics
        calls.append((dataset_id, level_id, target_id))
        return _failed_cell(
            dataset_id,
            level_id,
            target_id,
            message="stop here",
        )

    monkeypatch.setattr("snowiki.bench.runner.run_cell", _run_cell)

    result, exit_code = run_matrix_with_exit_code(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a", "dataset_b"),
            "level_ids": ("quick",),
            "target_ids": ("bm25_regex_v1",),
        },
        fail_fast=True,
    )

    assert exit_code == EXIT_CODE_PARTIAL_FAILURE
    assert len(result.cells) == 1
    assert calls == [("dataset_a", "quick", "bm25_regex_v1")]
    assert result.failures == ("stop here",)


@pytest.mark.parametrize(
    ("selection", "expected_message"),
    [
        ({"target_ids": ()}, "No benchmark targets selected."),
        (
            {
                "dataset_ids": ("missing_dataset",),
                "target_ids": ("bm25_regex_v1",),
            },
            "Unknown dataset selection: missing_dataset",
        ),
        (
            {
                "level_ids": ("missing_level",),
                "target_ids": ("bm25_regex_v1",),
            },
            "Unknown level selection: missing_level",
        ),
    ],
)
def test_invalid_input_returns_exit_code_2(
    selection: dict[str, tuple[str, ...]],
    expected_message: str,
) -> None:
    result, exit_code = run_matrix_with_exit_code(_matrix(), selection=selection)

    assert exit_code == EXIT_CODE_INVALID_INPUT
    assert result.cells == ()
    assert result.failures == (expected_message,)


def test_exit_codes_cover_success_partial_failure_and_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "snowiki.bench.runner.run_cell",
        lambda **kwargs: _success_cell(
            kwargs["dataset_id"], kwargs["level_id"], kwargs["target_id"]
        ),
    )
    _, success_exit = run_matrix_with_exit_code(
        _matrix(),
        selection={"target_ids": ("bm25_regex_v1",)},
    )

    monkeypatch.setattr(
        "snowiki.bench.runner.run_cell",
        lambda **kwargs: _failed_cell(
            kwargs["dataset_id"],
            kwargs["level_id"],
            kwargs["target_id"],
            message="cell failed",
        ),
    )
    _, partial_exit = run_matrix_with_exit_code(
        _matrix(),
        selection={"target_ids": ("bm25_regex_v1",)},
    )

    _, invalid_exit = run_matrix_with_exit_code(_matrix(), selection={"target_ids": ()})

    assert success_exit == EXIT_CODE_SUCCESS
    assert partial_exit == EXIT_CODE_PARTIAL_FAILURE
    assert invalid_exit == EXIT_CODE_INVALID_INPUT


def test_run_cell_applies_query_cap_to_judged_query_intersection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )
    received_query_ids: list[str] = []

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            received_query_ids.extend(query.query_id for query in queries)
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q4", query_text="four"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"d1"},
            "q3": {"d3"},
            "q4": {"d4"},
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    expected_query_ids = ["q1", "q3", "q4"]
    random.Random(1729).shuffle(expected_query_ids)

    assert result.status == "success"
    assert received_query_ids == expected_query_ids[:2]
    assert result.details["eligible_query_count"] == 3
    assert result.details["effective_query_count"] == 2
    assert result.details["sampling_seed"] == 1729


def test_run_cell_reports_slice_metrics_from_query_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=4)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            ranked_doc_ids_by_query_id = {
                "q1": ("doc-a", "miss", "doc-extra"),
                "q2": ("miss", "doc-b"),
                "q3": ("miss", "doc-c"),
                "q4": ("doc-d",),
            }
            latency_by_query_id = {
                "q1": 1.0,
                "q2": 10.0,
                "q3": 100.0,
                "q4": 1000.0,
            }
            return {
                "results": tuple(
                    QueryResult(
                        query_id=query.query_id,
                        ranked_doc_ids=ranked_doc_ids_by_query_id[query.query_id],
                        latency_ms=latency_by_query_id[query.query_id],
                    )
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(
                query_id="q1",
                query_text="한국어 known item",
                group="ko",
                kind="known-item",
                tags=("identifier-path-code-heavy", "hard-negative"),
            ),
            BenchmarkQuery(
                query_id="q2",
                query_text="mixed query",
                group="mixed",
            ),
            BenchmarkQuery(
                query_id="q3",
                query_text="English known item",
                group="en",
                kind="known-item",
                tags=("identifier-path-code-heavy",),
            ),
            BenchmarkQuery(
                query_id="q4",
                query_text="query without group",
                kind="topical",
                tags=(),
            ),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"doc-a", "doc-extra"},
            "q2": {"doc-b"},
            "q3": {"doc-c", "doc-missing"},
            "q4": {"doc-d"},
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
        metric_ids=(
            "recall_at_10",
            "hit_rate_at_1",
            "mrr_at_10",
            "ndcg_at_10",
            "latency_p50_ms",
            "latency_p95_ms",
        ),
    )

    slices = cast(dict[str, dict[str, object]], result.details["slices"])
    metrics_by_id = {metric.metric_id: metric for metric in result.metrics}
    per_query_scores = {
        metric_id: cast(dict[str, float], metric.details["per_query"])
        for metric_id, metric in metrics_by_id.items()
    }
    group_ko = slices["group:ko"]
    group_mixed = slices["group:mixed"]
    group_en = slices["group:en"]
    known_item = slices["kind:known-item"]
    topical = slices["kind:topical"]
    identifier_slice = slices["tag:identifier-path-code-heavy"]
    hard_negative_slice = slices["tag:hard-negative"]
    quality_metric_ids = (
        "recall_at_10",
        "hit_rate_at_1",
        "mrr_at_10",
        "ndcg_at_10",
    )
    expected_query_ids_by_slice = {
        "all": ("q1", "q2", "q3", "q4"),
        "group:ko": ("q1",),
        "group:mixed": ("q2",),
        "group:en": ("q3",),
        "kind:known-item": ("q1", "q3"),
        "kind:topical": ("q4",),
        "tag:identifier-path-code-heavy": ("q1", "q3"),
        "tag:hard-negative": ("q1",),
    }

    assert result.status == "success"
    assert "unknown" not in slices
    assert "group:unknown" not in slices
    assert "kind:unknown" not in slices
    assert "tag:unknown" not in slices
    assert group_ko["query_count"] == 1
    assert group_mixed["query_count"] == 1
    assert group_en["query_count"] == 1
    assert topical["query_count"] == 1
    assert identifier_slice["query_count"] == 2
    assert hard_negative_slice["query_count"] == 1
    assert known_item["query_count"] == 2

    for metric_id in quality_metric_ids:
        all_metrics = cast(dict[str, object], slices["all"]["metrics"])
        assert all_metrics[metric_id] == pytest.approx(metrics_by_id[metric_id].value)

    for slice_id, query_ids in expected_query_ids_by_slice.items():
        slice_metrics = cast(dict[str, object], slices[slice_id]["metrics"])
        evaluated_queries = cast(dict[str, object], slices[slice_id]["evaluated_queries"])
        for metric_id in quality_metric_ids:
            expected_value = sum(
                per_query_scores[metric_id][query_id] for query_id in query_ids
            ) / len(query_ids)
            assert slice_metrics[metric_id] == pytest.approx(expected_value)
            assert evaluated_queries[metric_id] == len(query_ids)

    for one_query_slice_id, query_id in {
        "group:ko": "q1",
        "group:mixed": "q2",
        "group:en": "q3",
        "kind:topical": "q4",
        "tag:hard-negative": "q1",
    }.items():
        slice_metrics = cast(dict[str, object], slices[one_query_slice_id]["metrics"])
        for metric_id in quality_metric_ids:
            assert slice_metrics[metric_id] == pytest.approx(
                per_query_scores[metric_id][query_id]
            )

    for slice_evidence in slices.values():
        slice_metrics = cast(dict[str, object], slice_evidence["metrics"])
        assert "latency_p50_ms" not in slice_metrics
        assert "latency_p95_ms" not in slice_metrics

    per_query = cast(dict[str, dict[str, object]], result.details["per_query"])
    assert set(per_query) == {"q1", "q2", "q3", "q4"}
    q1_evidence = per_query["q1"]
    assert q1_evidence["query"] == {
        "group": "ko",
        "kind": "known-item",
        "tags": ["identifier-path-code-heavy", "hard-negative"],
    }
    assert per_query["q2"]["query"] == {
        "group": "mixed",
        "kind": None,
        "tags": [],
    }
    assert per_query["q4"]["query"] == {
        "group": None,
        "kind": "topical",
        "tags": [],
    }
    assert q1_evidence["ranked_doc_ids"] == ["doc-a", "miss", "doc-extra"]
    assert q1_evidence["relevant_doc_ids"] == ["doc-a", "doc-extra"]
    assert q1_evidence["latency_ms"] == 1.0
    assert "hit_rate_at_1" in cast(dict[str, object], q1_evidence["metrics"])


def test_run_cell_preserves_query_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=1)},
    )
    diagnostics: dict[str, object] = {
        "retriever": "bm25",
        "tokenizer": "regex_v1",
        "query_tokens": ["needle", "alpha"],
        "top_hits": [
            {
                "rank": 1,
                "doc_id": "doc-b",
                "score": 1.25,
                "matched_terms": ["needle", "alpha"],
            }
        ],
    }

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
            include_diagnostics: bool = False,
        ) -> dict[str, object]:
            assert include_diagnostics is True
            del manifest, level, queries
            return {
                "results": (
                    QueryResult(
                        query_id="q1",
                        ranked_doc_ids=("doc-b",),
                        latency_ms=2.5,
                        diagnostics=diagnostics,
                    ),
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (BenchmarkQuery(query_id="q1", query_text="needle"),),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc-b"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
        include_diagnostics=True,
    )

    per_query = cast(dict[str, dict[str, object]], result.details["per_query"])
    assert per_query["q1"]["diagnostics"] == diagnostics


def test_run_cell_omits_query_diagnostics_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=1)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level, queries
            return {
                "results": (
                    QueryResult(
                        query_id="q1",
                        ranked_doc_ids=("doc-b",),
                        diagnostics={"query_tokens": ["sensitive"]},
                    ),
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (BenchmarkQuery(query_id="q1", query_text="needle"),),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc-b"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    per_query = cast(dict[str, dict[str, object]], result.details["per_query"])
    assert "diagnostics" not in per_query["q1"]


def test_run_cell_excludes_latency_metrics_from_slice_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            latencies = {"q1": 1.0, "q2": 100.0}
            return {
                "results": tuple(
                    QueryResult(
                        query_id=query.query_id,
                        ranked_doc_ids=("doc",),
                        latency_ms=latencies[query.query_id],
                    )
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(query_id="q1", query_text="one", group="ko"),
            BenchmarkQuery(query_id="q2", query_text="two", group="ko"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc"}, "q2": {"doc"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    slices = cast(dict[str, dict[str, object]], result.details["slices"])
    group_metrics = cast(dict[str, object], slices["group:ko"]["metrics"])

    assert "latency_p50_ms" not in group_metrics
    assert "latency_p95_ms" not in group_metrics


def test_run_cell_uses_deterministic_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=3)},
    )
    query_batches = [
        (
            BenchmarkQuery(query_id="q4", query_text="four"),
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
        (
            BenchmarkQuery(query_id="q3", query_text="three"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q4", query_text="four"),
        ),
    ]
    selections: list[tuple[str, ...]] = []

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            selections.append(tuple(query.query_id for query in queries))
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"d1"},
            "q3": {"d3"},
            "q4": {"d4"},
        },
    )

    load_count = {"value": 0}

    def _load_queries(
        manifest: DatasetManifest,
        **kwargs: object,
    ) -> tuple[BenchmarkQuery, ...]:
        del manifest, kwargs
        batch = query_batches[load_count["value"]]
        load_count["value"] += 1
        return batch

    monkeypatch.setattr("snowiki.bench.runner._load_materialized_queries", _load_queries)

    first_result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )
    second_result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    expected_query_ids = ["q1", "q3", "q4"]
    random.Random(1729).shuffle(expected_query_ids)

    assert first_result.status == "success"
    assert second_result.status == "success"
    assert selections == [tuple(expected_query_ids), tuple(expected_query_ids)]


def test_cell_details_include_sampling_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            return {
                "results": tuple(
                    QueryResult(
                        query_id=query.query_id,
                        ranked_doc_ids=(f"doc-{query.query_id}",),
                        latency_ms=1.5,
                    )
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"doc-q1"},
            "q2": {"doc-q2"},
            "q3": {"doc-q3"},
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    assert result.status == "success"
    assert result.details["eligible_query_count"] == 3
    assert result.details["effective_query_count"] == 2
    assert result.details["sampling_seed"] == 1729
    per_query = result.details["per_query"]
    assert isinstance(per_query, dict)
    assert len(per_query) == 2
    for evidence in per_query.values():
        assert evidence["latency_ms"] == 1.5
        assert isinstance(evidence["ranked_doc_ids"], list)
        assert isinstance(evidence["relevant_doc_ids"], list)
        assert isinstance(evidence["metrics"], dict)


def test_capped_run_cell_reports_smoke_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=1, corpus_cap=50)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (BenchmarkQuery(query_id="q1", query_text="one"),),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )
    rendered = render_json(BenchmarkRunResult(matrix_id="test_matrix", cells=(result,)))
    cells = cast(list[object], rendered["cells"])
    rendered_cell = cast(dict[str, object], cells[0])

    assert result.status == "success"
    assert result.details["run_classification"] == "smoke"
    assert result.details["public_baseline_comparable"] is False
    assert rendered_cell["run_classification"] == "smoke"
    assert rendered_cell["public_baseline_comparable"] is False


def test_run_cell_preserves_target_cache_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=1)},
    )
    cache_metadata = {
        "cache_hit": True,
        "cache_status": "hit",
        "cache_miss_reason": None,
        "cache_rebuilt": False,
        "cache_manifest_path": "/tmp/runtime/index/bench/bm25/manifest.json",
        "cache_schema_version": BM25_CACHE_SCHEMA_VERSION,
        "index_build_seconds": 0.0,
    }

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                ),
                "cache": cache_metadata,
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (BenchmarkQuery(query_id="q1", query_text="one"),),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="bm25_regex_v1",
    )

    assert result.status == "success"
    assert result.details["cache"] == cache_metadata
    rendered = render_json(
        BenchmarkRunResult(matrix_id="test_matrix", cells=(result,))
    )
    cells = cast(list[object], rendered["cells"])
    cell = cast(dict[str, object], cells[0])
    assert cell["cache"] == cache_metadata


def test_run_cell_omits_cache_metadata_when_adapter_does_not_report_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=1)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (BenchmarkQuery(query_id="q1", query_text="one"),),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {"q1": {"doc"}},
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
    )

    assert result.status == "success"
    assert "cache" not in result.details
    rendered = render_json(
        BenchmarkRunResult(matrix_id="test_matrix", cells=(result,))
    )
    cells = cast(list[object], rendered["cells"])
    cell = cast(dict[str, object], cells[0])
    assert "cache" not in cell


def test_run_cell_fails_when_target_omits_selected_query_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            return {
                "results": (
                    QueryResult(query_id=queries[0].query_id, ranked_doc_ids=("d1",)),
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q2", query_text="two"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"d1"},
            "q2": {"d2"},
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    expected_query_ids = ["q1", "q2"]
    random.Random(1729).shuffle(expected_query_ids)

    assert result.status == "failed"
    assert result.error_message == (
        "Cell execution failed: Benchmark target omitted results for selected queries: "
        f"{expected_query_ids[1]}"
    )


def test_run_cell_filters_to_queries_with_positive_qrels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=10)},
    )
    received_query_ids: list[str] = []

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            received_query_ids.extend(query.query_id for query in queries)
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("doc",))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest, **kwargs: (
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest, **kwargs: {
            "q1": {"d1"},
            "q3": {"d3"},
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    expected_query_ids = ["q1", "q3"]
    random.Random(1729).shuffle(expected_query_ids)

    assert result.status == "success"
    assert received_query_ids == expected_query_ids
    assert result.details["eligible_query_count"] == 2
    assert result.details["effective_query_count"] == 2


def test_run_cell_fails_for_missing_materialized_dataset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )
    adapter_called = False

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level, queries
            nonlocal adapter_called
            adapter_called = True
            return {"results": ()}

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner.resolve_dataset_assets",
        lambda manifest, **kwargs: {
            "corpus": tmp_path / "corpus.parquet",
            "queries": tmp_path / "queries.parquet",
            "judgments": tmp_path / "judgments.tsv",
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    assert result.status == "failed"
    assert result.error_message == (
        "Cell execution failed: Missing queries file: "
        f"{tmp_path / 'queries.parquet'} "
        "(run snowiki benchmark-fetch --dataset beir_nq --level quick)"
    )
    assert adapter_called is False


def test_run_cell_accepts_normalized_materialized_query_and_qrels_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )
    corpus_path = tmp_path / "corpus.parquet"
    queries_path = tmp_path / "queries.parquet"
    judgments_path = tmp_path / "judgments.tsv"

    _write_parquet(
        corpus_path,
        {"docid": ["d1", "d2"], "text": ["doc one", "doc two"]},
    )
    _write_parquet(
        queries_path,
        {"qid": ["q1", "q2"], "query": ["query one", "query two"]},
    )
    _ = judgments_path.write_text(
        "qid\tdocid\trelevance\nq1\td1\t1\nq2\td2\t2\n",
        encoding="utf-8",
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            return {
                "results": tuple(
                    QueryResult(
                        query_id=query.query_id,
                        ranked_doc_ids=("d1", "d2"),
                        latency_ms=1.0,
                    )
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner.resolve_dataset_assets",
        lambda manifest, **kwargs: {
            "corpus": corpus_path,
            "queries": queries_path,
            "judgments": judgments_path,
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    assert result.status == "success"
    assert result.details["eligible_query_count"] == 2
    assert result.details["effective_query_count"] == 2


def test_run_cell_accepts_json_queries_and_wrapped_judgments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )
    queries_path = tmp_path / "queries.json"
    judgments_path = tmp_path / "judgments.json"
    _ = queries_path.write_text(
        json.dumps(
            {
                "queries": [
                    {
                        "id": "q1",
                        "text": "한국어 질의",
                        "group": "ko",
                        "kind": "known-item",
                        "tags": ["identifier-path-code-heavy"],
                    },
                    {"id": "q2", "text": "English query", "group": "en"},
                ]
            }
        ),
        encoding="utf-8",
    )
    _ = judgments_path.write_text(
        json.dumps({"judgments": {"q1": ["d1"], "q2": ["d2"]}}),
        encoding="utf-8",
    )

    observed_queries: list[BenchmarkQuery] = []

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            del manifest, level
            observed_queries.extend(queries)
            return {
                "results": tuple(
                    QueryResult(query_id=query.query_id, ranked_doc_ids=("d1", "d2"))
                    for query in queries
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner.resolve_dataset_assets",
        lambda manifest, **kwargs: {
            "corpus": tmp_path / "corpus.parquet",
            "queries": queries_path,
            "judgments": judgments_path,
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    assert result.status == "success"
    assert {query.query_id for query in observed_queries} == {"q1", "q2"}
    q1 = next(query for query in observed_queries if query.query_id == "q1")
    assert q1.group == "ko"
    assert q1.kind == "known-item"
    assert q1.tags == ("identifier-path-code-heavy",)
    assert "group:ko" in result.details["slices"]


def _write_parquet(path: Path, data: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = Dataset.from_dict(data)
    _ = dataset.to_parquet(path.as_posix())
