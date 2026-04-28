from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import CliRunner, Result

from snowiki.cli.main import app

pytestmark = pytest.mark.smoke

REQUIRED_QUERY_IDS = {
    "cli_tool_command",
    "session_history",
    "source_provenance",
}
REQUIRED_SLICE_IDS = {
    "group:ko",
    "group:en",
    "group:mixed",
    "kind:known-item",
    "kind:topical",
    "kind:temporal",
    "tag:hard-negative",
    "tag:identifier-path-code-heavy",
}
FIRST_SCREEN_METRICS = {
    "recall_at_5",
    "hit_rate_at_5",
    "mrr_at_10",
    "ndcg_at_10",
}


def _invoke_benchmark(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark", *args])


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _metrics_by_id(metrics: object) -> dict[str, float]:
    assert isinstance(metrics, list)
    by_id: dict[str, float] = {}
    for metric in metrics:
        assert isinstance(metric, dict)
        metric_mapping = cast(Mapping[str, object], metric)
        metric_id = metric_mapping["metric_id"]
        value = metric_mapping["value"]
        assert isinstance(metric_id, str)
        assert isinstance(value, int | float)
        by_id[metric_id] = float(value)
    return by_id


def test_snowiki_regression_matrix_smoke_contract(
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
    assert payload["matrix_id"] == "snowiki_regression"
    assert payload["selection"] == {
        "dataset_ids": ["snowiki_retrieval_regression"],
        "level_ids": ["regression"],
        "target_ids": ["bm25_regex_v1"],
        "metric_ids": [
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
        ],
    }
    assert payload["summary"] == {
        "total_cells": 1,
        "success_count": 1,
        "failure_count": 0,
    }

    cells = payload["cells"]
    assert isinstance(cells, list)
    assert len(cells) == 1
    cell = cells[0]
    assert isinstance(cell, dict)
    assert cell["dataset_id"] == "snowiki_retrieval_regression"
    assert cell["level_id"] == "regression"
    assert cell["target_id"] == "bm25_regex_v1"
    assert cell["status"] == "success"
    assert cell["error"] is None

    metrics = _metrics_by_id(cell["metrics"])
    assert set(metrics) >= FIRST_SCREEN_METRICS
    assert metrics["hit_rate_at_5"] >= 0.85
    assert metrics["recall_at_5"] >= 0.85
    assert metrics["mrr_at_10"] >= 0.80
    assert metrics["ndcg_at_10"] >= 0.85

    per_query = cell["per_query"]
    assert isinstance(per_query, dict)
    assert len(per_query) == 23
    assert set(per_query) >= REQUIRED_QUERY_IDS
    for query_id in REQUIRED_QUERY_IDS:
        evidence = per_query[query_id]
        assert isinstance(evidence, dict)
        query_metrics = evidence["metrics"]
        assert isinstance(query_metrics, dict)
        assert query_metrics["hit_rate_at_5"] == 1.0

    slices = cell["slices"]
    assert isinstance(slices, dict)
    assert set(slices) >= REQUIRED_SLICE_IDS
    for slice_id in REQUIRED_SLICE_IDS:
        slice_evidence = slices[slice_id]
        assert isinstance(slice_evidence, dict)
        slice_metrics = slice_evidence["metrics"]
        assert isinstance(slice_metrics, dict)
        assert slice_metrics["hit_rate_at_5"] >= 0.5
    assert slices["group:ko"]["metrics"]["hit_rate_at_5"] < 1.0
