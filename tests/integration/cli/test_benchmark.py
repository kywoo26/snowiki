from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

import pytest
from click.testing import CliRunner, Result

from snowiki.cli.main import app

pytestmark = pytest.mark.integration

DEFAULT_METRIC_IDS = [
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
]


def _write_benchmark_fixture_repo(repo_root: Path, *, dataset_ids: tuple[str, ...]) -> None:
    contracts_dir = repo_root / "benchmarks" / "contracts"
    manifests_dir = contracts_dir / "datasets"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    datasets_block = "".join(f"  - {dataset_id}\n" for dataset_id in dataset_ids)
    matrix_text = (
        "matrix_id: official_core\n"
        + "datasets:\n"
        + datasets_block
        + "levels:\n"
        + "  quick:\n"
        + "    query_cap: 150\n"
    )
    _ = (contracts_dir / "official_matrix.yaml").write_text(
        matrix_text,
        encoding="utf-8",
    )
    for dataset_id in dataset_ids:
        _ = (manifests_dir / f"{dataset_id}.yaml").write_text(
            dedent(
                f"""\
                dataset_id: {dataset_id}
                name: Tiny fixture {dataset_id}
                language: en
                purpose_tags:
                  - test
                corpus_path: benchmarks/materialized/{dataset_id}/corpus.parquet
                queries_path: benchmarks/materialized/{dataset_id}/queries.parquet
                judgments_path: benchmarks/materialized/{dataset_id}/judgments.tsv
                source:
                  corpus:
                    repo_id: local/test
                    config: {dataset_id}
                    split: corpus
                    revision: corpus-{dataset_id}-v1
                  queries:
                    repo_id: local/test
                    config: {dataset_id}
                    split: queries
                    revision: queries-{dataset_id}-v1
                  judgments:
                    repo_id: local/test
                    config: {dataset_id}
                    split: judgments
                    revision: judgments-{dataset_id}-v1
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


def _patch_temp_benchmark_repo(
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
) -> None:
    import snowiki.config as config

    config.get_repo_root.cache_clear()
    monkeypatch.setattr("snowiki.config.get_repo_root", lambda: repo_root)


def _patch_fake_benchmark_fetch_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    rows_by_split: dict[str, list[dict[str, object]]] = {
        "corpus": [
            {"id": "doc-alpha", "text": "alpha token unique"},
            {"id": "doc-delta", "text": "delta token unique"},
        ],
        "queries": [
            {"id": "q-alpha", "text": "alpha"},
            {"id": "q-delta", "text": "delta"},
        ],
        "judgments": [
            {"qid": "q-alpha", "docid": "doc-alpha", "relevance": 1},
            {"qid": "q-delta", "docid": "doc-delta", "relevance": 1},
        ],
    }

    def _fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        streaming: bool = False,
    ) -> list[dict[str, object]]:
        del repo_id, config, revision, cache_dir, streaming
        return rows_by_split[split]

    monkeypatch.setattr("snowiki.benchmark_fetch.load_dataset", _fake_load_dataset)


def _matrix_path(repo_root: Path) -> Path:
    return repo_root / "benchmarks" / "contracts" / "official_matrix.yaml"


def _invoke_benchmark(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark", *args])


def _invoke_benchmark_fetch(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark-fetch", *args])


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def test_benchmark_help_shows_lean_option_surface() -> None:
    result = _invoke_benchmark("--help")

    assert result.exit_code == 0
    for option in (
        "--matrix FILE",
        "--report FILE",
        "--dataset TEXT",
        "--level TEXT",
        "--target TEXT",
        "--metric TEXT",
        "--fail-fast / --no-fail-fast",
    ):
        assert option in result.output


def test_benchmark_run_succeeds_after_materializing_temp_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    dataset_id = "tiny_success"
    _write_benchmark_fixture_repo(repo_root, dataset_ids=(dataset_id,))
    _patch_temp_benchmark_repo(monkeypatch, repo_root)
    _patch_fake_benchmark_fetch_loader(monkeypatch)

    output_path = tmp_path / "benchmark.json"

    materialize = _invoke_benchmark_fetch("--dataset", dataset_id)

    assert materialize.exit_code == 0, materialize.output
    assert (
        f"dataset={dataset_id} level=quick action=materialized reason=missing_sidecar "
        "corpus=2 queries=2 judgments=2"
    ) in materialize.output

    result = _invoke_benchmark(
        "--matrix",
        str(_matrix_path(repo_root)),
        "--dataset",
        dataset_id,
        "--level",
        "quick",
        "--target",
        "snowiki_query_runtime_v1",
        "--report",
        str(output_path),
    )

    assert result.exit_code == 0, result.output
    assert "matrix=official_core cells=1 failures=0" in result.output

    payload = _read_json(output_path)
    assert payload["matrix_id"] == "official_core"
    assert payload["selection"] == {
        "dataset_ids": [dataset_id],
        "level_ids": ["quick"],
        "target_ids": ["snowiki_query_runtime_v1"],
        "metric_ids": DEFAULT_METRIC_IDS,
    }
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 1,
        "failure_count": 0,
    }
    assert set(payload) == {
        "generated_at",
        "matrix_id",
        "selection",
        "summary",
        "cells",
    }

    cells = payload["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 1
    cell = cells[0]
    assert isinstance(cell, dict)
    assert cell["dataset_id"] == dataset_id
    assert cell["level_id"] == "quick"
    assert cell["target_id"] == "snowiki_query_runtime_v1"
    assert cell["status"] == "success"
    assert cell["error"] is None

    metrics = cell["metrics"]
    assert isinstance(metrics, list)
    assert metrics == [
        {"metric_id": "recall_at_1", "value": 1.0},
        {"metric_id": "recall_at_3", "value": 1.0},
        {"metric_id": "recall_at_5", "value": 1.0},
        {"metric_id": "recall_at_10", "value": 1.0},
        {"metric_id": "recall_at_100", "value": 1.0},
        {"metric_id": "hit_rate_at_1", "value": 1.0},
        {"metric_id": "hit_rate_at_3", "value": 1.0},
        {"metric_id": "hit_rate_at_5", "value": 1.0},
        {"metric_id": "hit_rate_at_10", "value": 1.0},
        {"metric_id": "mrr_at_10", "value": 1.0},
        {"metric_id": "ndcg_at_10", "value": 1.0},
    ]
    latency = cell["latency"]
    assert isinstance(latency, dict)
    assert isinstance(latency["p50"], float)
    assert isinstance(latency["p95"], float)
    per_query = cell["per_query"]
    assert isinstance(per_query, dict)
    assert set(per_query) == {"q-alpha", "q-delta"}
    for evidence in per_query.values():
        assert isinstance(evidence, dict)
        metrics_by_query = evidence["metrics"]
        assert isinstance(metrics_by_query, dict)
        assert metrics_by_query["recall_at_1"] == 1.0
        assert metrics_by_query["recall_at_3"] == 1.0
        assert metrics_by_query["recall_at_5"] == 1.0
        assert metrics_by_query["recall_at_10"] == 1.0
        assert metrics_by_query["recall_at_100"] == 1.0
        assert metrics_by_query["hit_rate_at_1"] == 1.0
        assert metrics_by_query["hit_rate_at_3"] == 1.0
        assert metrics_by_query["hit_rate_at_5"] == 1.0
        assert metrics_by_query["hit_rate_at_10"] == 1.0
        assert metrics_by_query["mrr_at_10"] == 1.0
        assert metrics_by_query["ndcg_at_10"] == 1.0


def test_benchmark_bm25_reports_cache_metadata_and_hits_on_repeat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    runtime_root = tmp_path / "runtime"
    dataset_id = "tiny_bm25_cache"
    monkeypatch.setenv("SNOWIKI_ROOT", runtime_root.as_posix())
    _write_benchmark_fixture_repo(repo_root, dataset_ids=(dataset_id,))
    _patch_temp_benchmark_repo(monkeypatch, repo_root)
    _patch_fake_benchmark_fetch_loader(monkeypatch)
    materialize = _invoke_benchmark_fetch("--dataset", dataset_id)

    assert materialize.exit_code == 0, materialize.output

    first_output_path = tmp_path / "benchmark-first.json"
    second_output_path = tmp_path / "benchmark-second.json"
    benchmark_args = (
        "--matrix",
        str(_matrix_path(repo_root)),
        "--dataset",
        dataset_id,
        "--level",
        "quick",
        "--target",
        "bm25_regex_v1",
    )

    first = _invoke_benchmark(*benchmark_args, "--report", str(first_output_path))
    second = _invoke_benchmark(*benchmark_args, "--report", str(second_output_path))

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert "matrix=official_core cells=1 failures=0" in first.output
    assert "matrix=official_core cells=1 failures=0" in second.output
    first_cell = _read_json(first_output_path)["cells"][0]
    second_cell = _read_json(second_output_path)["cells"][0]
    assert isinstance(first_cell, dict)
    assert isinstance(second_cell, dict)

    first_cache = first_cell["cache"]
    second_cache = second_cell["cache"]
    assert isinstance(first_cache, dict)
    assert isinstance(second_cache, dict)
    assert first_cache["cache_hit"] is False
    assert first_cache["cache_status"] == "rebuilt"
    assert first_cache["cache_miss_reason"] == "missing_manifest"
    assert first_cache["cache_rebuilt"] is True
    assert isinstance(first_cache["index_build_seconds"], float)
    assert first_cache["index_build_seconds"] >= 0.0
    assert Path(cast(str, first_cache["cache_manifest_path"])).is_file()
    assert second_cache["cache_hit"] is True
    assert second_cache["cache_status"] == "hit"
    assert second_cache["cache_miss_reason"] is None
    assert second_cache["cache_rebuilt"] is False
    assert second_cache["index_build_seconds"] == 0.0


def test_benchmark_missing_materialized_dataset_reports_fetch_guidance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    dataset_id = "tiny_missing"
    _write_benchmark_fixture_repo(repo_root, dataset_ids=(dataset_id,))
    _patch_temp_benchmark_repo(monkeypatch, repo_root)

    output_path = tmp_path / "missing-materialized.json"

    result = _invoke_benchmark(
        "--matrix",
        str(_matrix_path(repo_root)),
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
    assert "matrix=official_core cells=1 failures=1" in result.output

    payload = _read_json(output_path)
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 0,
        "failure_count": 1,
    }
    assert payload["cells"] == [
        {
            "dataset_id": dataset_id,
            "level_id": "quick",
            "target_id": "snowiki_query_runtime_v1",
            "status": "failed",
            "metrics": [],
            "latency": None,
            "per_query": {},
            "slices": {},
            "error": (
                "Cell execution failed: Missing queries file: "
                f"{repo_root / 'benchmarks' / 'materialized' / dataset_id / 'quick' / 'queries.parquet'} "
                f"(run snowiki benchmark-fetch --dataset {dataset_id} --level quick)"
            ),
        }
    ]


def test_benchmark_missing_report_fails_in_click_validation() -> None:
    result = _invoke_benchmark("--target", "snowiki_query_runtime_v1")

    assert result.exit_code == 2
    assert "Missing option '--report'." in result.output


def test_benchmark_invalid_dataset_reports_clear_error(tmp_path: Path) -> None:
    output_path = tmp_path / "invalid-dataset.json"
    result = _invoke_benchmark(
        "--dataset",
        "missing_dataset",
        "--target",
        "snowiki_query_runtime_v1",
        "--report",
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
        "snowiki_query_runtime_v1",
        "--report",
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
        "--report",
        str(output_path),
    )

    assert result.exit_code == 2
    assert "Unknown target selection: missing_target" in result.output
    assert not output_path.exists()


def test_benchmark_fail_fast_stops_after_first_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    missing_dataset_id = "tiny_missing"
    materialized_dataset_id = "tiny_materialized"
    _write_benchmark_fixture_repo(
        repo_root,
        dataset_ids=(missing_dataset_id, materialized_dataset_id),
    )
    _patch_temp_benchmark_repo(monkeypatch, repo_root)
    _patch_fake_benchmark_fetch_loader(monkeypatch)

    materialize = _invoke_benchmark_fetch("--dataset", materialized_dataset_id)

    assert materialize.exit_code == 0, materialize.output

    output_path = tmp_path / "fail-fast.json"

    result = _invoke_benchmark(
        "--matrix",
        str(_matrix_path(repo_root)),
        "--dataset",
        missing_dataset_id,
        "--dataset",
        materialized_dataset_id,
        "--level",
        "quick",
        "--target",
        "snowiki_query_runtime_v1",
        "--fail-fast",
        "--report",
        str(output_path),
    )

    assert result.exit_code == 1, result.output
    assert "matrix=official_core cells=1 failures=1" in result.output
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
    assert dataset_id == missing_dataset_id
    assert status == "failed"


def test_benchmark_gate_cli_evaluates_report_and_writes_output(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    report_path = tmp_path / "benchmark-report.json"
    gate_report_path = tmp_path / "gate-report.json"
    _ = gate_path.write_text(
        dedent(
            """\
            gate_id: korean_analyzer_promotion_v1
            baseline_target: bm25_regex_v1
            candidate_targets:
              - bm25_kiwi_morphology_v1
            public_matrix:
              matrix: benchmarks/contracts/official_matrix.yaml
              required_dataset_ids:
                - miracl_ko
              required_level_ids:
                - standard
            snowiki_slices:
              required_slice_ids:
                - group:ko
              required_golden_query_ids:
                - cli_tool_command
            thresholds:
              public_korean:
                dataset_id: miracl_ko
                slice_id: all
                must_improve_metrics:
                  ndcg_at_10:
                    min_relative_delta: 0.03
                  recall_at_100:
                    min_relative_delta: 0.03
              snowiki_korean:
                slice_id: group:ko
                must_improve_metrics:
                  hit_rate_at_5:
                    min_relative_delta: 0.03
                  mrr_at_10:
                    min_relative_delta: 0.03
              mixed_and_identifier_regression:
                slice_ids: []
                max_allowed_absolute_regression: 0.0
                metrics: []
              temporal_regression:
                slice_id: kind:temporal
                max_allowed_absolute_regression: 0.0
                metrics: []
              golden_query_regression:
                fixture: fixtures/retrieval/golden_queries.json
                required_query_ids:
                  - cli_tool_command
                max_allowed_top5_regressions: 0
              public_english_regression:
                dataset_ids: []
                slice_id: all
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              english_regression:
                slice_id: group:en
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              latency:
                max_p95_multiplier_vs_baseline: 1.5
            """
        ),
        encoding="utf-8",
    )
    _ = report_path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "dataset_id": "miracl_ko",
                        "level_id": "standard",
                        "target_id": "bm25_regex_v1",
                        "status": "success",
                        "metrics": [
                            {"metric_id": "ndcg_at_10", "value": 0.35},
                            {"metric_id": "recall_at_100", "value": 0.72},
                            {"metric_id": "hit_rate_at_5", "value": 0.50},
                            {"metric_id": "mrr_at_10", "value": 0.40},
                        ],
                        "latency": {"p50": 2.0, "p95": 5.0},
                        "per_query": {
                            "cli_tool_command": {
                                "metrics": {"hit_rate_at_5": 1.0},
                            }
                        },
                        "slices": {
                            "all": {
                                "metrics": {
                                    "ndcg_at_10": 0.35,
                                    "recall_at_100": 0.72,
                                },
                            },
                            "group:ko": {
                                "metrics": {"hit_rate_at_5": 0.50, "mrr_at_10": 0.40},
                            },
                        },
                        "error": None,
                    },
                    {
                        "dataset_id": "miracl_ko",
                        "level_id": "standard",
                        "target_id": "bm25_kiwi_morphology_v1",
                        "status": "success",
                        "metrics": [
                            {"metric_id": "ndcg_at_10", "value": 0.41},
                            {"metric_id": "recall_at_100", "value": 0.75},
                            {"metric_id": "hit_rate_at_5", "value": 0.55},
                            {"metric_id": "mrr_at_10", "value": 0.43},
                        ],
                        "latency": {"p50": 2.1, "p95": 5.1},
                        "per_query": {
                            "cli_tool_command": {
                                "metrics": {"hit_rate_at_5": 1.0},
                            }
                        },
                        "slices": {
                            "all": {
                                "metrics": {
                                    "ndcg_at_10": 0.41,
                                    "recall_at_100": 0.75,
                                },
                            },
                            "group:ko": {
                                "metrics": {"hit_rate_at_5": 0.55, "mrr_at_10": 0.43},
                            },
                        },
                        "error": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark-gate",
            "--gate",
            str(gate_path),
            "--report",
            str(report_path),
            "--gate-report",
            str(gate_report_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "gate=korean_analyzer_promotion_v1 candidates=1 status=pass failures=0" in result.output
    payload = _read_json(gate_report_path)
    assert payload["status"] == "pass"
    assert payload["summary"] == {
        "candidate_count": 1,
        "pass_count": 1,
        "fail_count": 0,
        "failure_count": 0,
    }


def test_benchmark_gate_cli_writes_failing_gate_report(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    report_path = tmp_path / "benchmark-report.json"
    gate_report_path = tmp_path / "gate-report.json"
    _ = gate_path.write_text(
        dedent(
            """\
            gate_id: korean_analyzer_promotion_v1
            baseline_target: bm25_regex_v1
            candidate_targets:
              - bm25_kiwi_morphology_v1
            public_matrix:
              matrix: benchmarks/contracts/official_matrix.yaml
              required_dataset_ids:
                - miracl_ko
              required_level_ids:
                - standard
            snowiki_slices:
              required_slice_ids: []
              required_golden_query_ids: []
            thresholds:
              public_korean:
                dataset_id: miracl_ko
                slice_id: all
                must_improve_metrics:
                  ndcg_at_10:
                    min_relative_delta: 0.03
              snowiki_korean:
                slice_id: group:ko
                must_improve_metrics: {}
              mixed_and_identifier_regression:
                slice_ids: []
                max_allowed_absolute_regression: 0.0
                metrics: []
              temporal_regression:
                slice_id: kind:temporal
                max_allowed_absolute_regression: 0.0
                metrics: []
              golden_query_regression:
                fixture: fixtures/retrieval/golden_queries.json
                required_query_ids: []
                max_allowed_top5_regressions: 0
              public_english_regression:
                dataset_ids: []
                slice_id: all
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              english_regression:
                slice_id: group:en
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              latency:
                max_p95_multiplier_vs_baseline: 1.5
            """
        ),
        encoding="utf-8",
    )
    _ = report_path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "dataset_id": "miracl_ko",
                        "level_id": "standard",
                        "target_id": "bm25_regex_v1",
                        "status": "success",
                        "metrics": [{"metric_id": "ndcg_at_10", "value": 0.40}],
                        "latency": {"p95": 5.0},
                        "per_query": {},
                        "slices": {},
                        "error": None,
                    },
                    {
                        "dataset_id": "miracl_ko",
                        "level_id": "standard",
                        "target_id": "bm25_kiwi_morphology_v1",
                        "status": "success",
                        "metrics": [{"metric_id": "ndcg_at_10", "value": 0.40}],
                        "latency": {"p95": 5.1},
                        "per_query": {},
                        "slices": {},
                        "error": None,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "benchmark-gate",
            "--gate",
            str(gate_path),
            "--report",
            str(report_path),
            "--gate-report",
            str(gate_report_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=fail" in result.output
    payload = _read_json(gate_report_path)
    assert payload["status"] == "fail"
    assert payload["summary"] == {
        "candidate_count": 1,
        "pass_count": 0,
        "fail_count": 1,
        "failure_count": 1,
    }


def test_benchmark_gate_missing_report_fails_in_click_validation(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    _ = gate_path.write_text("gate_id: x\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["benchmark-gate", "--gate", str(gate_path)])

    assert result.exit_code == 2
    assert "Missing option '--report'." in result.output


def test_benchmark_gate_malformed_report_uses_click_error(tmp_path: Path) -> None:
    gate_path = tmp_path / "gate.yaml"
    report_path = tmp_path / "bad-report.json"
    _ = gate_path.write_text(
        dedent(
            """\
            gate_id: korean_analyzer_promotion_v1
            baseline_target: bm25_regex_v1
            candidate_targets:
              - bm25_kiwi_morphology_v1
            public_matrix:
              matrix: benchmarks/contracts/official_matrix.yaml
              required_dataset_ids:
                - miracl_ko
              required_level_ids:
                - standard
            snowiki_slices:
              required_slice_ids: []
              required_golden_query_ids: []
            thresholds:
              public_korean:
                dataset_id: miracl_ko
                slice_id: all
                must_improve_metrics: {}
              snowiki_korean:
                slice_id: group:ko
                must_improve_metrics: {}
              mixed_and_identifier_regression:
                slice_ids: []
                max_allowed_absolute_regression: 0.0
                metrics: []
              temporal_regression:
                slice_id: kind:temporal
                max_allowed_absolute_regression: 0.0
                metrics: []
              golden_query_regression:
                fixture: fixtures/retrieval/golden_queries.json
                required_query_ids: []
                max_allowed_top5_regressions: 0
              public_english_regression:
                dataset_ids: []
                slice_id: all
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              english_regression:
                slice_id: group:en
                max_allowed_absolute_regression: 0.005
                max_allowed_relative_regression: 0.01
                metrics: []
              latency:
                max_p95_multiplier_vs_baseline: 1.5
            """
        ),
        encoding="utf-8",
    )
    _ = report_path.write_text("{bad json", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark-gate", "--gate", str(gate_path), "--report", str(report_path)],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_benchmark_gate_malformed_gate_uses_click_error(tmp_path: Path) -> None:
    gate_path = tmp_path / "bad-gate.yaml"
    report_path = tmp_path / "report.json"
    _ = gate_path.write_text("gate_id: [unterminated\n", encoding="utf-8")
    _ = report_path.write_text('{"cells": []}\n', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark-gate", "--gate", str(gate_path), "--report", str(report_path)],
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_benchmark_runs_snowiki_regression_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    report_path = tmp_path / "snowiki-regression.json"

    result = _invoke_benchmark(
        "--matrix",
        "benchmarks/contracts/snowiki_regression_matrix.yaml",
        "--level",
        "regression",
        "--target",
        "bm25_regex_v1",
        "--report",
        str(report_path),
    )

    assert result.exit_code == 0, result.output
    assert "matrix=snowiki_regression cells=1 failures=0" in result.output
    payload = _read_json(report_path)
    cell = payload["cells"][0]
    assert isinstance(cell, dict)
    assert cell["dataset_id"] == "snowiki_retrieval_regression"
    assert cell["status"] == "success"
    per_query = cell["per_query"]
    assert isinstance(per_query, dict)
    assert len(per_query) == 20
    slices = cell["slices"]
    assert isinstance(slices, dict)
    assert {
        "group:ko",
        "group:en",
        "group:mixed",
        "kind:known-item",
        "kind:topical",
        "kind:temporal",
        "tag:hard-negative",
        "tag:identifier-path-code-heavy",
    } <= set(slices)
