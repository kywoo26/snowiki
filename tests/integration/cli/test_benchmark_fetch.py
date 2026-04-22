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


def test_benchmark_fetch_command_reports_paths(
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
                "dataset_id": dataset_id,
                "data_root": data_root,
                "refresh": refresh,
                "local_files_only": local_files_only,
            }
        )
        return BenchmarkDatasetFetchResult(
            dataset_id="beir_scifact",
            benchmark_data_root=benchmark_root,
            sources=(
                BenchmarkDatasetSourceFetch(
                    label="corpus_queries",
                    name="BEIR SciFact corpus and queries",
                    repo_id="BeIR/scifact",
                    repo_type="dataset",
                    requested_revision="main",
                    snapshot_path=snapshot_path,
                    allow_patterns=("corpus/*.parquet", "queries/*.parquet"),
                ),
                BenchmarkDatasetSourceFetch(
                    label="qrels",
                    name="BEIR SciFact qrels",
                    repo_id="BeIR/scifact-qrels",
                    repo_type="dataset",
                    requested_revision="main",
                    snapshot_path=qrels_snapshot_path,
                    allow_patterns=("test.tsv",),
                ),
            ),
            lock_path=lock_path,
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
        "dataset_id": "beir_scifact",
        "data_root": benchmark_root,
        "refresh": "force",
        "local_files_only": True,
    }
    assert "dataset id: beir_scifact" in result.output
    assert f"benchmark data root: {benchmark_root}" in result.output
    assert f"lock path: {lock_path}" in result.output
    assert "source count: 2" in result.output
    assert "- corpus_queries: BeIR/scifact @ main" in result.output
    assert f"  snapshot path: {snapshot_path}" in result.output
    assert "  allow patterns: corpus/*.parquet, queries/*.parquet" in result.output
    assert "- qrels: BeIR/scifact-qrels @ main" in result.output
    assert f"  snapshot path: {qrels_snapshot_path}" in result.output
    assert "  allow patterns: test.tsv" in result.output


def test_benchmark_fetch_help_mentions_supported_datasets() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["benchmark-fetch", "--help"])

    assert result.exit_code == 0, result.output
    assert "miracl_ko" in result.output
    assert "beir_scifact" in result.output
    assert "beir_nfcorpus" in result.output
