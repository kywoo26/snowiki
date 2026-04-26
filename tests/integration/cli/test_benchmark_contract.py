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


def _write_missing_materialized_benchmark_repo(repo_root: Path, dataset_id: str) -> Path:
    contracts_dir = repo_root / "benchmarks" / "contracts"
    manifests_dir = contracts_dir / "datasets"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = contracts_dir / "official_matrix.yaml"
    _ = matrix_path.write_text(
        dedent(
            f"""\
            matrix_id: official_core
            datasets:
              - {dataset_id}
            levels:
              quick:
                query_cap: 150
            """
        ),
        encoding="utf-8",
    )
    _ = (manifests_dir / f"{dataset_id}.yaml").write_text(
        dedent(
            f"""\
            dataset_id: {dataset_id}
            name: Missing materialized fixture
            language: en
            purpose_tags:
              - test
            corpus_path: benchmarks/materialized/{dataset_id}/corpus.parquet
            queries_path: benchmarks/materialized/{dataset_id}/queries.parquet
            judgments_path: benchmarks/materialized/{dataset_id}/judgments.tsv
            source:
              corpus:
                repo_id: BeIR/scifact
                config: corpus
                split: corpus
                revision: b3b5335604bf5ee3c4447671af975ea25143d4f5
              queries:
                repo_id: BeIR/scifact
                config: queries
                split: queries
                revision: b3b5335604bf5ee3c4447671af975ea25143d4f5
              judgments:
                repo_id: BeIR/scifact-qrels
                config: default
                split: test
                revision: 2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029
            field_mappings:
              corpus_id_keys:
                - id
              corpus_text_keys:
                - text
              query_id_keys:
                - id
              query_text_keys:
                - text
              judgment_query_id_keys:
                - qid
              judgment_doc_id_keys:
                - docid
              judgment_relevance_keys:
                - relevance
            supported_levels:
              - quick
            """
        ),
        encoding="utf-8",
    )
    return matrix_path


def _patch_temp_repo(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    import snowiki.config as config

    config.get_repo_root.cache_clear()
    monkeypatch.setattr("snowiki.config.get_repo_root", lambda: repo_root)


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


def test_benchmark_json_output_uses_lean_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_id = "missing_fixture"
    matrix_path = _write_missing_materialized_benchmark_repo(
        tmp_path / "benchmark-repo",
        dataset_id,
    )
    _patch_temp_repo(monkeypatch, tmp_path / "benchmark-repo")
    output_path = tmp_path / "benchmark.json"

    result = _invoke_benchmark(
        "--matrix",
        str(matrix_path),
        "--dataset",
        dataset_id,
        "--level",
        "quick",
        "--target",
        "snowiki_query_runtime_v1",
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
        "target_ids": ["snowiki_query_runtime_v1"],
        "metric_ids": ["recall_at_100"],
    }
    success_result = BenchmarkRunResult(
        matrix_id="official_core",
        cells=(
            CellResult(
                dataset_id="beir_nq",
                level_id="quick",
                target_id="snowiki_query_runtime_v1",
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
            "snowiki_query_runtime_v1",
            "--report",
            str(output_path),
        )
    assert success.exit_code == 0, success.output

    missing_dataset_id = "missing_fixture"
    matrix_path = _write_missing_materialized_benchmark_repo(
        tmp_path / "benchmark-repo",
        missing_dataset_id,
    )
    _patch_temp_repo(monkeypatch, tmp_path / "benchmark-repo")

    partial_failure = _invoke_benchmark(
        "--matrix",
        str(matrix_path),
        "--dataset",
        missing_dataset_id,
        "--level",
        "quick",
        "--target",
        "snowiki_query_runtime_v1",
        "--report",
        str(tmp_path / "partial-failure.json"),
    )
    assert partial_failure.exit_code == 1, partial_failure.output

    invalid_input = _invoke_benchmark(
        "--dataset",
        "missing_dataset",
        "--target",
        "snowiki_query_runtime_v1",
        "--report",
        str(tmp_path / "invalid-input.json"),
    )
    assert invalid_input.exit_code == 2, invalid_input.output
