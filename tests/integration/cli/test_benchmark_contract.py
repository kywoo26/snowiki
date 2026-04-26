from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner, Result

from snowiki.bench.specs import BenchmarkRunResult, CellResult
from snowiki.cli.main import app

EXPECTED_HELP = dedent(
    """\
    Usage: snowiki benchmark [OPTIONS]

      Run the lean benchmark skeleton against a matrix contract.

    Options:
      --matrix FILE                 Evaluation matrix contract to run.  [default:
                                    benchmarks/contracts/official_matrix.yaml]
      --report FILE                 Path to write the benchmark JSON result.
                                    [required]
      --dataset TEXT                Dataset ID to run. Repeat to select multiple
                                    datasets.
      --level TEXT                  Level ID to run. Repeat to select multiple
                                    levels.
      --target TEXT                 Target ID to run. Repeat to select multiple
                                    targets.
      --metric TEXT                 Metric ID to compute. Repeat to select multiple
                                    metrics.
      --fail-fast / --no-fail-fast  Stop after the first failed matrix cell.
                                    [default: no-fail-fast]
      -h, --help                    Show this message and exit.
    """
)


def _invoke_benchmark(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark", *args])


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_benchmark_help_text_matches_expected_lean_surface() -> None:
    result = _invoke_benchmark("--help")

    assert result.exit_code == 0
    assert result.output == EXPECTED_HELP


def test_benchmark_help_omits_legacy_option_surface() -> None:
    result = _invoke_benchmark("--help")

    assert result.exit_code == 0
    for option in ("--preset", "--sample-mode", "--layer", "--root"):
        assert option not in result.output


def test_benchmark_json_output_uses_lean_schema(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.json"

    result = _invoke_benchmark(
        "--dataset",
        "trec_dl_2020_passage",
        "--level",
        "quick",
        "--target",
        "lexical_regex_v1",
        "--report",
        str(output_path),
    )

    assert result.exit_code == 1, result.output
    payload = _read_json(output_path)
    assert set(payload) == {
        "generated_at",
        "matrix_id",
        "selection",
        "summary",
        "cells",
    }
    for legacy_key in (
        "_".join(("benchmark", "verdict")),
        "performance_thresholds",
        "performance_threshold_policy",
        "report_version",
    ):
        assert legacy_key not in payload


def test_benchmark_exit_codes_cover_success_partial_failure_and_invalid_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "success.json"
    selection = {
        "dataset_ids": ["beir_nq"],
        "level_ids": ["quick"],
        "target_ids": ["lexical_regex_v1"],
        "metric_ids": ["recall_at_100"],
    }
    success_result = BenchmarkRunResult(
        matrix_id="official_core",
        cells=(
            CellResult(
                dataset_id="beir_nq",
                level_id="quick",
                target_id="lexical_regex_v1",
                status="success",
            ),
        ),
        details={"selection": selection},
    )

    with monkeypatch.context() as context:
        context.setattr(
        "snowiki.cli.commands.benchmark.run_matrix_with_exit_code",
            lambda matrix, selection, fail_fast=False: (success_result, 0),
        )
        success = _invoke_benchmark(
            "--dataset",
            "beir_nq",
            "--level",
            "quick",
            "--target",
            "lexical_regex_v1",
            "--report",
            str(output_path),
        )
    assert success.exit_code == 0, success.output

    partial_failure = _invoke_benchmark(
        "--dataset",
        "trec_dl_2020_passage",
        "--level",
        "quick",
        "--target",
        "lexical_regex_v1",
        "--report",
        str(tmp_path / "partial-failure.json"),
    )
    assert partial_failure.exit_code == 1, partial_failure.output

    invalid_input = _invoke_benchmark(
        "--dataset",
        "missing_dataset",
        "--target",
        "lexical_regex_v1",
        "--report",
        str(tmp_path / "invalid-input.json"),
    )
    assert invalid_input.exit_code == 2, invalid_input.output
