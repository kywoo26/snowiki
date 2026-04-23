from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import CliRunner, Result

from snowiki.cli.main import app


def _invoke_benchmark(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark", *args])


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def test_benchmark_help_shows_lean_option_surface() -> None:
    result = _invoke_benchmark("--help")

    assert result.exit_code == 0
    for option in (
        "--matrix FILE",
        "--output FILE",
        "--dataset TEXT",
        "--level TEXT",
        "--target TEXT",
        "--metric TEXT",
        "--fail-fast / --no-fail-fast",
    ):
        assert option in result.output


def test_benchmark_run_writes_json_and_reports_stub_failure(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.json"

    result = _invoke_benchmark(
        "--dataset",
        "ms_marco_passage",
        "--level",
        "quick",
        "--target",
        "lexical_regex_v1",
        "--output",
        str(output_path),
    )

    assert result.exit_code == 1, result.output
    assert "matrix=official_six cells=1 failures=1" in result.output
    assert (
        "Benchmark target lexical_regex_v1 is registered but not executable yet."
        in result.output
    )

    payload = _read_json(output_path)
    assert payload["matrix_id"] == "official_six"
    assert payload["selection"] == {
        "dataset_ids": ["ms_marco_passage"],
        "level_ids": ["quick"],
        "target_ids": ["lexical_regex_v1"],
        "metric_ids": [
            "recall_at_100",
            "mrr_at_10",
            "ndcg_at_10",
            "latency_p50_ms",
            "latency_p95_ms",
        ],
    }
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 0,
        "failure_count": 1,
    }
    assert payload["cells"] == [
        {
            "dataset_id": "ms_marco_passage",
            "level_id": "quick",
            "target_id": "lexical_regex_v1",
            "status": "failed",
            "metrics": [],
            "latency": None,
            "per_query": {},
            "error": "Cell execution failed: Benchmark target lexical_regex_v1 is registered but not executable yet.",
        }
    ]


def test_benchmark_missing_output_fails_in_click_validation() -> None:
    result = _invoke_benchmark("--target", "lexical_regex_v1")

    assert result.exit_code == 2
    assert "Missing option '--output'." in result.output


def test_benchmark_invalid_dataset_reports_clear_error(tmp_path: Path) -> None:
    output_path = tmp_path / "invalid-dataset.json"
    result = _invoke_benchmark(
        "--dataset",
        "missing_dataset",
        "--target",
        "lexical_regex_v1",
        "--output",
        str(output_path),
    )

    assert result.exit_code == 2
    assert "Unknown dataset selection: missing_dataset" in result.output
    assert not output_path.exists()


def test_benchmark_invalid_level_reports_clear_error(tmp_path: Path) -> None:
    output_path = tmp_path / "invalid-level.json"
    result = _invoke_benchmark(
        "--level",
        "missing_level",
        "--target",
        "lexical_regex_v1",
        "--output",
        str(output_path),
    )

    assert result.exit_code == 2
    assert "Unknown level selection: missing_level" in result.output
    assert not output_path.exists()


def test_benchmark_invalid_target_reports_clear_error(tmp_path: Path) -> None:
    output_path = tmp_path / "invalid-target.json"
    result = _invoke_benchmark(
        "--target",
        "missing_target",
        "--output",
        str(output_path),
    )

    assert result.exit_code == 2
    assert "Unknown target selection: missing_target" in result.output
    assert not output_path.exists()


def test_benchmark_fail_fast_stops_after_first_failure(tmp_path: Path) -> None:
    output_path = tmp_path / "fail-fast.json"

    result = _invoke_benchmark(
        "--dataset",
        "ms_marco_passage",
        "--dataset",
        "beir_nq",
        "--level",
        "quick",
        "--target",
        "lexical_regex_v1",
        "--fail-fast",
        "--output",
        str(output_path),
    )

    assert result.exit_code == 1, result.output
    payload = _read_json(output_path)
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 0,
        "failure_count": 1,
    }
    cells = payload["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 1
    first_cell = cells[0]
    assert isinstance(first_cell, dict)
    dataset_id = first_cell["dataset_id"]  # noqa: B018
    status = first_cell["status"]  # noqa: B018
    assert dataset_id == "ms_marco_passage"
    assert status == "failed"
