from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from snowiki.bench.datasets import (
    BenchmarkDatasetFetchResult,
    BenchmarkDatasetId,
    BenchmarkDatasetSourceFetch,
    RefreshMode,
)
from snowiki.cli.commands import benchmark_fetch as benchmark_fetch_command
from snowiki.cli.main import app

_TERMINAL_WIDTH = 80
_EXPECTED_BENCHMARK_FETCH_HELP_LINES = (
    "Usage: snowiki benchmark-fetch [OPTIONS]",
    "",
    "Options:",
    "  --dataset [ms_marco_passage|trec_dl_2020_passage|miracl_ko|miracl_en|beir_nq|beir_scifact]",
    "                                  Official benchmark dataset to fetch into the",
    "                                  benchmark-owned cache.  [required]",
    "  --data-root DIRECTORY           Override the benchmark data root used for the",
    "                                  HF cache and local locks.",
    "  --refresh [if-missing|force]    Reuse an existing local lock when possible or",
    "                                  force a fresh snapshot fetch.  [default: if-",
    "                                  missing]",
    "  --offline / --no-offline        Require the dataset snapshot to already exist",
    "                                  in the local benchmark cache.  [default: no-",
    "                                  offline]",
    "  -h, --help                      Show this message and exit.",
)
_EXPECTED_FETCH_DATASETS = (
    "ms_marco_passage",
    "trec_dl_2020_passage",
    "miracl_ko",
    "miracl_en",
    "beir_nq",
    "beir_scifact",
)


def test_benchmark_fetch_help_text_matches_frozen_contract() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark-fetch", "--help"],
        terminal_width=_TERMINAL_WIDTH,
    )

    assert result.exit_code == 0, result.output
    assert result.output.splitlines() == list(_EXPECTED_BENCHMARK_FETCH_HELP_LINES)


def test_benchmark_fetch_supported_dataset_choices_match_frozen_contract() -> None:
    assert benchmark_fetch_command.OFFICIAL_FETCH_DATASET_IDS == _EXPECTED_FETCH_DATASETS


def test_benchmark_fetch_success_contract_exits_zero_and_reports_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    benchmark_root = tmp_path / "bench-root"
    snapshot_path = benchmark_root / "hf" / "datasets--BeIR--scifact" / "snapshots" / "abc"
    qrels_snapshot_path = (
        benchmark_root / "hf" / "datasets--BeIR--scifact-qrels" / "snapshots" / "qrels"
    )
    lock_path = benchmark_root / "locks" / "beir_scifact.json"
    captured: dict[str, object] = {}

    def fake_fetch_benchmark_dataset(
        dataset_id: BenchmarkDatasetId,
        *,
        data_root: Path | None,
        refresh: RefreshMode,
        local_files_only: bool,
    ) -> BenchmarkDatasetFetchResult:
        captured.update(
            {
                "data_root": data_root,
                "dataset_id": dataset_id,
                "local_files_only": local_files_only,
                "refresh": refresh,
            }
        )
        return BenchmarkDatasetFetchResult(
            benchmark_data_root=benchmark_root,
            dataset_id="beir_scifact",
            lock_path=lock_path,
            sources=(
                BenchmarkDatasetSourceFetch(
                    allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
                    label="corpus_queries",
                    name="BEIR SciFact corpus and queries",
                    repo_id="BeIR/scifact",
                    repo_type="dataset",
                    requested_revision="main",
                    snapshot_path=snapshot_path,
                ),
                BenchmarkDatasetSourceFetch(
                    allow_patterns=("test.tsv",),
                    label="qrels",
                    name="BEIR SciFact qrels",
                    repo_id="BeIR/scifact-qrels",
                    repo_type="dataset",
                    requested_revision="main",
                    snapshot_path=qrels_snapshot_path,
                ),
            ),
        )

    monkeypatch.setattr(
        benchmark_fetch_command,
        "fetch_benchmark_dataset",
        fake_fetch_benchmark_dataset,
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark-fetch",
            "--dataset",
            "beir_scifact",
            "--data-root",
            str(benchmark_root),
            "--refresh",
            "force",
            "--offline",
        ],
        env={"SNOWIKI_ROOT": str(tmp_path / "root")},
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "data_root": benchmark_root,
        "dataset_id": "beir_scifact",
        "local_files_only": True,
        "refresh": "force",
    }
    assert result.output.splitlines() == [
        "dataset id: beir_scifact",
        f"benchmark data root: {benchmark_root}",
        f"lock path: {lock_path}",
        "source count: 2",
        "- corpus_queries: BeIR/scifact @ main",
        f"  snapshot path: {snapshot_path}",
        "  allow patterns: corpus/*.parquet, queries/*.parquet",
        "- qrels: BeIR/scifact-qrels @ main",
        f"  snapshot path: {qrels_snapshot_path}",
        "  allow patterns: test.tsv",
    ]


def test_benchmark_fetch_invalid_dataset_uses_click_usage_exit_code() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark-fetch", "--dataset", "not_a_dataset"],
        terminal_width=_TERMINAL_WIDTH,
    )

    assert result.exit_code == 2, result.output
    assert result.output.splitlines() == [
        "Usage: snowiki benchmark-fetch [OPTIONS]",
        "Try 'snowiki benchmark-fetch -h' for help.",
        "",
        "Error: Invalid value for '--dataset': 'not_a_dataset' is not one of 'ms_marco_passage', 'trec_dl_2020_passage', 'miracl_ko', 'miracl_en', 'beir_nq', 'beir_scifact'.",
    ]
