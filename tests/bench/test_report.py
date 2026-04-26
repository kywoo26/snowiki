from __future__ import annotations

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
        details={"per_query": {"q1": {"score": 1.0}}},
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
        "error",
    }
    assert set(success_payload) == expected_keys
    assert set(failed_payload) == expected_keys
    assert success_payload["metrics"] == [{"metric_id": "recall_at_100", "value": 0.75}]
    assert success_payload["latency"] == {"p50": 11.0, "p95": 22.0}
    assert success_payload["per_query"] == {"q1": {"score": 1.0}}
    assert success_payload["error"] is None
    assert failed_payload["metrics"] == []
    assert failed_payload["latency"] is None
    assert failed_payload["per_query"] == {}
    assert failed_payload["error"] == "boom"


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
