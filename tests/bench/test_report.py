from __future__ import annotations

from typing import cast

from snowiki.bench.report import _render_cell, render_json, render_summary
from snowiki.bench.specs import BenchmarkRunResult, CellResult, MetricResult


def test_render_json_returns_expected_top_level_keys() -> None:
    result = BenchmarkRunResult(
        matrix_id="official_core",
        cells=(
            CellResult(
                dataset_id="beir_nq",
                level_id="quick",
                target_id="snowiki_query_runtime_v1",
                status="success",
                metrics=(MetricResult(metric_id="recall_at_100", value=0.75),),
            ),
        ),
        details={"selection": {"dataset_ids": ["beir_nq"]}},
    )

    payload = render_json(result)

    assert set(payload) == {"generated_at", "matrix_id", "selection", "summary", "cells"}
    assert payload["matrix_id"] == "official_core"
    assert payload["selection"] == {"dataset_ids": ["beir_nq"]}
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 1,
        "failure_count": 0,
    }
    assert "report_version" not in payload


def test_render_cell_uses_stable_schema_for_success_and_failure() -> None:
    success_cell = CellResult(
        dataset_id="beir_scifact",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
        status="success",
        metrics=(
            MetricResult(metric_id="recall_at_100", value=0.75),
            MetricResult(metric_id="latency_p50_ms", value=11.0),
            MetricResult(metric_id="latency_p95_ms", value=22.0),
        ),
        details={
            "per_query": {
                "q1": {
                    "score": 1.0,
                    "diagnostics": {
                        "query_tokens": ["alpha"],
                        "top_hits": [{"doc_id": "doc-alpha", "score": 2.0}],
                    },
                }
            }
        },
    )
    failed_cell = CellResult(
        dataset_id="beir_scifact",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
        status="failed",
        error_message="boom",
    )

    success_payload = _render_cell(success_cell)
    failed_payload = _render_cell(failed_cell)

    expected_keys = {
        "dataset_id",
        "level_id",
        "target_id",
        "status",
        "metrics",
        "latency",
        "per_query",
        "slices",
        "error",
    }
    assert set(success_payload) == expected_keys
    assert set(failed_payload) == expected_keys
    assert success_payload["metrics"] == [{"metric_id": "recall_at_100", "value": 0.75}]
    metrics = cast(list[dict[str, object]], success_payload["metrics"])
    metric_ids = {m["metric_id"] for m in metrics}
    assert "latency_p50_ms" not in metric_ids
    assert "latency_p95_ms" not in metric_ids
    assert success_payload["latency"] == {"p50": 11.0, "p95": 22.0}
    assert success_payload["per_query"] == {
        "q1": {
            "score": 1.0,
            "diagnostics": {
                "query_tokens": ["alpha"],
                "top_hits": [{"doc_id": "doc-alpha", "score": 2.0}],
            },
        }
    }
    assert success_payload["slices"] == {}
    assert success_payload["error"] is None
    assert failed_payload["metrics"] == []
    assert failed_payload["latency"] is None
    assert failed_payload["per_query"] == {}
    assert failed_payload["slices"] == {}
    assert failed_payload["error"] == "boom"
    assert "report_version" not in success_payload
    assert "report_version" not in failed_payload


def test_render_summary_uses_expected_format() -> None:
    result = BenchmarkRunResult(
        matrix_id="official_core",
        cells=(
            CellResult(
                dataset_id="beir_scifact",
                level_id="quick",
                target_id="snowiki_query_runtime_v1",
                status="failed",
                error_message="boom",
            ),
        ),
        failures=("boom",),
    )

    assert render_summary(result) == "matrix=official_core cells=1 failures=1"


def test_render_cell_includes_optional_keys_only_when_present() -> None:
    cell_with_optional = CellResult(
        dataset_id="beir_scifact",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
        status="success",
        metrics=(MetricResult(metric_id="recall_at_100", value=0.75),),
        details={
            "run_classification": "regression",
            "public_baseline_comparable": True,
            "cache": {"hits": 42, "misses": 1},
        },
    )
    cell_without_optional = CellResult(
        dataset_id="beir_scifact",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
        status="success",
        metrics=(MetricResult(metric_id="recall_at_100", value=0.75),),
        details={},
    )

    payload_with = _render_cell(cell_with_optional)
    payload_without = _render_cell(cell_without_optional)

    assert "run_classification" in payload_with
    assert payload_with["run_classification"] == "regression"
    assert "public_baseline_comparable" in payload_with
    assert payload_with["public_baseline_comparable"] is True
    assert "cache" in payload_with
    assert payload_with["cache"] == {"hits": 42, "misses": 1}

    assert "run_classification" not in payload_without
    assert "public_baseline_comparable" not in payload_without
    assert "cache" not in payload_without


def test_render_cell_excludes_optional_keys_with_wrong_types() -> None:
    cell_wrong_types = CellResult(
        dataset_id="beir_scifact",
        level_id="quick",
        target_id="snowiki_query_runtime_v1",
        status="success",
        metrics=(MetricResult(metric_id="recall_at_100", value=0.75),),
        details={
            "run_classification": 123,
            "public_baseline_comparable": "yes",
            "cache": "not_a_dict",
        },
    )

    payload = _render_cell(cell_wrong_types)

    assert "run_classification" not in payload
    assert "public_baseline_comparable" not in payload
    assert "cache" not in payload
