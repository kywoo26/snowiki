from __future__ import annotations

from collections.abc import Sequence

import pytest

from snowiki.bench.runner import (
    EXIT_CODE_INVALID_INPUT,
    EXIT_CODE_PARTIAL_FAILURE,
    EXIT_CODE_SUCCESS,
    run_matrix,
    run_matrix_with_exit_code,
)
from snowiki.bench.specs import CellResult, EvaluationMatrix, LevelConfig


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
