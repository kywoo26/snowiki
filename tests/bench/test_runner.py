from __future__ import annotations

import random
from collections.abc import Sequence
from pathlib import Path

import pytest
from datasets import Dataset

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
    CellResult,
    DatasetManifest,
    EvaluationMatrix,
    LevelConfig,
    QueryResult,
)


def _matrix() -> EvaluationMatrix:
    return EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("dataset_a", "dataset_b"),
        levels={
            "quick": LevelConfig(level_id="quick", query_cap=10),
            "full": LevelConfig(level_id="full", query_cap=100),
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
    ) -> CellResult:
        del matrix
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
                "recall_at_100",
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
    ) -> CellResult:
        del matrix, metric_ids
        calls.append((dataset_id, level_id, target_id))
        return _success_cell(dataset_id, level_id, target_id)

    monkeypatch.setattr("snowiki.bench.runner.run_cell", _run_cell)

    result, exit_code = run_matrix_with_exit_code(
        _matrix(),
        selection={
            "dataset_ids": ("dataset_a", "dataset_b"),
            "level_ids": ("quick", "full"),
            "target_ids": ("bm25_regex_v1",),
        },
    )

    assert exit_code == EXIT_CODE_SUCCESS
    assert len(result.cells) == 4
    assert calls == [
        ("dataset_a", "quick", "bm25_regex_v1"),
        ("dataset_a", "full", "bm25_regex_v1"),
        ("dataset_b", "quick", "bm25_regex_v1"),
        ("dataset_b", "full", "bm25_regex_v1"),
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
    ) -> CellResult:
        del matrix, metric_ids
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
    ) -> CellResult:
        del matrix, metric_ids
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
        lambda manifest: (
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q4", query_text="four"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest: {
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
        lambda manifest: {
            "q1": {"d1"},
            "q3": {"d3"},
            "q4": {"d4"},
        },
    )

    load_count = {"value": 0}

    def _load_queries(manifest: DatasetManifest) -> tuple[BenchmarkQuery, ...]:
        del manifest
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
        lambda manifest: (
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest: {
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
        lambda manifest: (
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q2", query_text="two"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest: {
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
        lambda manifest: (
            BenchmarkQuery(query_id="q2", query_text="two"),
            BenchmarkQuery(query_id="q1", query_text="one"),
            BenchmarkQuery(query_id="q3", query_text="three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest: {
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
        lambda manifest: {
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
        "(run snowiki benchmark-fetch --dataset beir_nq)"
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
        lambda manifest: {
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


def _write_parquet(path: Path, data: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = Dataset.from_dict(data)
    _ = dataset.to_parquet(path.as_posix())
