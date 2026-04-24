from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from .specs import BenchmarkRunResult, CellResult, MetricResult


def render_json(result: BenchmarkRunResult) -> dict[str, object]:
    """Render a lean JSON-serializable result payload."""

    success_count = sum(1 for cell in result.cells if cell.status == "success")
    failure_count = sum(1 for cell in result.cells if cell.status == "failed")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "matrix_id": result.matrix_id,
        "selection": dict(
            cast(dict[str, object], result.details.get("selection", {}))
        ),
        "summary": {
            "total_cells": len(result.cells),
            "success_count": success_count,
            "failure_count": failure_count,
        },
        "cells": [_render_cell(cell) for cell in result.cells],
    }


def render_summary(result: BenchmarkRunResult) -> str:
    """Render a short human-readable summary of a benchmark run."""

    return (
        f"matrix={result.matrix_id} cells={len(result.cells)} "
        f"failures={len(result.failures)}"
    )


def _render_cell(cell: CellResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "dataset_id": cell.dataset_id,
        "level_id": cell.level_id,
        "target_id": cell.target_id,
        "status": cell.status,
        "metrics": [],
        "latency": None,
        "per_query": {},
        "error": None,
    }
    if cell.status == "success":
        payload["metrics"] = [
            _render_metric(metric)
            for metric in cell.metrics
            if metric.metric_id not in {"latency_p50_ms", "latency_p95_ms"}
        ]
        payload["latency"] = {
            "p50": _metric_value(cell.metrics, "latency_p50_ms"),
            "p95": _metric_value(cell.metrics, "latency_p95_ms"),
        }
        payload["per_query"] = dict(
            cast(dict[str, object], cell.details.get("per_query", {}))
        )
        run_classification = cell.details.get("run_classification")
        if isinstance(run_classification, str):
            payload["run_classification"] = run_classification
        public_baseline_comparable = cell.details.get("public_baseline_comparable")
        if isinstance(public_baseline_comparable, bool):
            payload["public_baseline_comparable"] = public_baseline_comparable
        cache_metadata = cell.details.get("cache")
        if isinstance(cache_metadata, dict):
            payload["cache"] = dict(cast(dict[str, object], cache_metadata))
    if cell.status == "failed" and cell.error_message is not None:
        payload["error"] = cell.error_message
    return payload


def _render_metric(metric: MetricResult) -> dict[str, object]:
    return {
        "metric_id": metric.metric_id,
        "value": metric.value,
    }


def _metric_value(metrics: tuple[MetricResult, ...], metric_id: str) -> float | None:
    for metric in metrics:
        if metric.metric_id == metric_id:
            return metric.value
    return None
