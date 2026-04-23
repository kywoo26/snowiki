from __future__ import annotations

import math

import pytest

from snowiki.bench.metrics import (
    BUILTIN_METRICS,
    DEFAULT_METRIC_REGISTRY,
    MetricRegistry,
)
from snowiki.bench.runner import run_cell
from snowiki.bench.specs import (
    DatasetManifest,
    EvaluationMatrix,
    LevelConfig,
    MetricResult,
    QueryResult,
)


def _stub_metric(results: object, qrels: object) -> MetricResult:
    del results, qrels
    return MetricResult(metric_id="stub_metric", value=1.0)


def test_builtin_metric_registry_lists_all_five_metrics() -> None:
    expected = (
        "recall_at_100",
        "mrr_at_10",
        "ndcg_at_10",
        "latency_p50_ms",
        "latency_p95_ms",
    )

    assert expected == BUILTIN_METRICS
    assert DEFAULT_METRIC_REGISTRY.list_metrics() == expected


def test_recall_at_100_computes_expected_average() -> None:
    results = (
        QueryResult(query_id="q1", ranked_doc_ids=("d1", "d3", "d2")),
        QueryResult(query_id="q2", ranked_doc_ids=("x1", "x2", "x3")),
    )
    qrels = {
        "q1": {"d1", "d2"},
        "q2": {"x4"},
    }

    metric = DEFAULT_METRIC_REGISTRY.compute("recall_at_100", results, qrels)

    assert metric.metric_id == "recall_at_100"
    assert metric.value == 0.5
    assert metric.details["per_query"] == {"q1": 1.0, "q2": 0.0}


def test_mrr_at_10_computes_expected_average() -> None:
    results = (
        QueryResult(query_id="q1", ranked_doc_ids=("d9", "d1", "d2")),
        QueryResult(query_id="q2", ranked_doc_ids=("x1", "x2", "x3")),
    )
    qrels = {
        "q1": {"d1", "d2"},
        "q2": {"x3"},
    }

    metric = DEFAULT_METRIC_REGISTRY.compute("mrr_at_10", results, qrels)

    assert metric.metric_id == "mrr_at_10"
    assert metric.value == pytest.approx((0.5 + (1.0 / 3.0)) / 2.0)
    assert metric.details["per_query"] == pytest.approx({"q1": 0.5, "q2": 1.0 / 3.0})


def test_ndcg_at_10_computes_expected_average() -> None:
    results = (
        QueryResult(query_id="q1", ranked_doc_ids=("d1", "x", "d2")),
        QueryResult(query_id="q2", ranked_doc_ids=("x1", "x2", "x3")),
    )
    qrels = {
        "q1": {"d1", "d2"},
        "q2": {"x3"},
    }

    metric = DEFAULT_METRIC_REGISTRY.compute("ndcg_at_10", results, qrels)
    expected_q1 = (1.0 + (1.0 / math.log2(4))) / (1.0 + (1.0 / math.log2(3)))
    expected_q2 = 1.0 / math.log2(4)

    assert metric.metric_id == "ndcg_at_10"
    assert metric.value == pytest.approx((expected_q1 + expected_q2) / 2.0)
    assert metric.details["per_query"] == pytest.approx(
        {"q1": expected_q1, "q2": expected_q2}
    )


def test_latency_p50_ms_computes_expected_percentile() -> None:
    results = (
        QueryResult(query_id="q1", ranked_doc_ids=("d1",), latency_ms=10.0),
        QueryResult(query_id="q2", ranked_doc_ids=("d2",), latency_ms=20.0),
        QueryResult(query_id="q3", ranked_doc_ids=("d3",), latency_ms=30.0),
        QueryResult(query_id="q4", ranked_doc_ids=("d4",), latency_ms=40.0),
    )

    metric = DEFAULT_METRIC_REGISTRY.compute("latency_p50_ms", results, {})

    assert metric.metric_id == "latency_p50_ms"
    assert metric.value == 25.0
    assert metric.details["per_query"] == {
        "q1": 10.0,
        "q2": 20.0,
        "q3": 30.0,
        "q4": 40.0,
    }


def test_latency_p95_ms_computes_expected_percentile() -> None:
    results = (
        QueryResult(query_id="q1", ranked_doc_ids=("d1",), latency_ms=10.0),
        QueryResult(query_id="q2", ranked_doc_ids=("d2",), latency_ms=20.0),
        QueryResult(query_id="q3", ranked_doc_ids=("d3",), latency_ms=30.0),
        QueryResult(query_id="q4", ranked_doc_ids=("d4",), latency_ms=40.0),
    )

    metric = DEFAULT_METRIC_REGISTRY.compute("latency_p95_ms", results, {})

    assert metric.metric_id == "latency_p95_ms"
    assert metric.value == pytest.approx(38.5)
    assert metric.details["per_query"] == {
        "q1": 10.0,
        "q2": 20.0,
        "q3": 30.0,
        "q4": 40.0,
    }


def test_unknown_metric_raises_clear_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark metric: missing_metric"):
        DEFAULT_METRIC_REGISTRY.compute("missing_metric", (), {})


def test_duplicate_registration_raises_value_error() -> None:
    registry = MetricRegistry()

    registry.register_metric("duplicate_metric", _stub_metric)

    with pytest.raises(ValueError, match="Metric already registered: duplicate_metric"):
        registry.register_metric("duplicate_metric", _stub_metric)


def test_run_cell_executes_adapter_and_computes_all_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = DatasetManifest(
        dataset_id="beir_nq",
        name="BEIR Natural Questions",
        language="en",
        purpose_tags=("passage-retrieval",),
        corpus_path="benchmarks/datasets/beir_nq/corpus.parquet",
        queries_path="benchmarks/datasets/beir_nq/queries.parquet",
        judgments_path="benchmarks/datasets/beir_nq/judgments.tsv",
        field_mappings={},
        supported_levels=("quick",),
    )
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            return {
                "results": (
                    QueryResult(
                        query_id="q1", ranked_doc_ids=("d1", "d9"), latency_ms=10.0
                    ),
                    QueryResult(
                        query_id="q2",
                        ranked_doc_ids=("x1", "x2", "x3"),
                        latency_ms=20.0,
                    ),
                ),
                "qrels": {
                    "q1": {"d1"},
                    "q2": {"x3"},
                },
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())

    result = run_cell(
        matrix=matrix, dataset_id="beir_nq", level_id="quick", target_id="test_target"
    )

    assert result.status == "success"
    assert result.error_message is None
    assert tuple(metric.metric_id for metric in result.metrics) == BUILTIN_METRICS
    assert result.details["per_query"] == {
        "q1": {
            "ranked_doc_ids": ["d1", "d9"],
            "relevant_doc_ids": ["d1"],
            "latency_ms": 10.0,
            "metrics": {
                "recall_at_100": 1.0,
                "mrr_at_10": 1.0,
                "ndcg_at_10": 1.0,
                "latency_p50_ms": 10.0,
                "latency_p95_ms": 10.0,
            },
        },
        "q2": {
            "ranked_doc_ids": ["x1", "x2", "x3"],
            "relevant_doc_ids": ["x3"],
            "latency_ms": 20.0,
            "metrics": {
                "recall_at_100": 1.0,
                "mrr_at_10": 1.0 / 3.0,
                "ndcg_at_10": 1.0 / math.log2(4),
                "latency_p50_ms": 20.0,
                "latency_p95_ms": 20.0,
            },
        },
    }
