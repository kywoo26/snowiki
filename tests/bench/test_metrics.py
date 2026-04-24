from __future__ import annotations

import math
import random
from pathlib import Path
from typing import cast

import pytest
from datasets import Dataset

from snowiki.bench.cache import (
    BM25_CACHE_SCHEMA_VERSION,
    build_bm25_cache_identity,
    load_or_rebuild_bm25_cache,
)
from snowiki.bench.metrics import (
    BUILTIN_METRICS,
    DEFAULT_METRIC_REGISTRY,
    MetricRegistry,
)
from snowiki.bench.runner import run_cell
from snowiki.bench.specs import (
    BenchmarkQuery,
    DatasetManifest,
    EvaluationMatrix,
    LevelConfig,
    MetricResult,
    QueryResult,
)
from snowiki.storage.zones import StoragePaths


def test_bm25_cache_reports_disabled_or_unwritable_and_cleans_temp_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_paths = StoragePaths(tmp_path / "runtime")
    identity = _cache_identity()

    def _raise_replace(source: object, destination: object) -> None:
        del source, destination
        raise PermissionError("cache directory is unwritable")

    monkeypatch.setattr("snowiki.storage.zones.os.replace", _raise_replace)

    result = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=identity,
        build_artifact=lambda: (b"uncached", b"uncached"),
        load_artifact=lambda path: path.read_bytes(),
    )

    assert result.value == b"uncached"
    assert result.metadata == {
        "cache_hit": False,
        "cache_status": "disabled_or_unwritable",
        "cache_miss_reason": "unwritable_cache_directory",
        "cache_rebuilt": True,
        "cache_manifest_path": cast(str, result.metadata["cache_manifest_path"]),
        "cache_schema_version": BM25_CACHE_SCHEMA_VERSION,
        "index_build_seconds": cast(float, result.metadata["index_build_seconds"]),
    }
    assert cast(float, result.metadata["index_build_seconds"]) >= 0.0
    manifest_path = Path(cast(str, result.metadata["cache_manifest_path"]))
    assert not manifest_path.exists()
    assert list(manifest_path.parent.glob("*.tmp")) == []


def _stub_metric(results: object, qrels: object) -> MetricResult:
    del results, qrels
    return MetricResult(metric_id="stub_metric", value=1.0)


def _cache_identity() -> dict[str, object]:
    return build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture/corpus.parquet",
        corpus_hash="hash",
        corpus_cap=10,
        documents=(("doc-a", "alpha"),),
        tokenizer_name="regex_v1",
        tokenizer_config={"family": "regex"},
        tokenizer_version=1,
        bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
    )


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
        corpus_path="benchmarks/materialized/beir_nq/corpus.parquet",
        queries_path="benchmarks/materialized/beir_nq/queries.parquet",
        judgments_path="benchmarks/materialized/beir_nq/judgments.tsv",
        field_mappings={
            "query_id_keys": ("_id",),
            "query_text_keys": ("text",),
            "judgment_query_id_keys": ("query-id",),
            "judgment_doc_id_keys": ("corpus-id",),
            "judgment_relevance_keys": ("score",),
        },
        supported_levels=("quick",),
    )
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=2)},
    )
    query_text_by_id = {
        "q1": "query one",
        "q2": "query two",
    }
    expected_query_ids = ["q1", "q2"]
    random.Random(1729).shuffle(expected_query_ids)
    expected_queries = tuple(
        BenchmarkQuery(query_id=query_id, query_text=query_text_by_id[query_id])
        for query_id in expected_query_ids
    )

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            assert queries == expected_queries
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
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner._load_materialized_queries",
        lambda manifest: (
            BenchmarkQuery(query_id="q1", query_text="query one"),
            BenchmarkQuery(query_id="q2", query_text="query two"),
            BenchmarkQuery(query_id="q3", query_text="query three"),
        ),
    )
    monkeypatch.setattr(
        "snowiki.bench.runner._load_qrels",
        lambda manifest: {
            "q1": {"d1"},
            "q2": {"x3"},
        },
    )

    result = run_cell(
        matrix=matrix, dataset_id="beir_nq", level_id="quick", target_id="test_target"
    )

    assert result.status == "success"
    assert result.error_message is None
    assert tuple(metric.metric_id for metric in result.metrics) == BUILTIN_METRICS
    assert result.details["eligible_query_count"] == 2
    assert result.details["effective_query_count"] == 2
    assert result.details["sampling_seed"] == 1729
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


def test_graded_qrels_binary_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = DatasetManifest(
        dataset_id="beir_nq",
        name="BEIR Natural Questions",
        language="en",
        purpose_tags=("passage-retrieval",),
        corpus_path=(tmp_path / "corpus.parquet").as_posix(),
        queries_path=(tmp_path / "queries.parquet").as_posix(),
        judgments_path=(tmp_path / "judgments.tsv").as_posix(),
        field_mappings={
            "query_id_keys": ("qid",),
            "query_text_keys": ("query",),
            "judgment_query_id_keys": ("qid",),
            "judgment_doc_id_keys": ("docid",),
            "judgment_relevance_keys": ("relevance",),
        },
        supported_levels=("quick",),
    )
    matrix = EvaluationMatrix(
        matrix_id="test_matrix",
        datasets=("beir_nq",),
        levels={"quick": LevelConfig(level_id="quick", query_cap=10)},
    )
    _write_parquet(
        Path(manifest.queries_path),
        {
            "qid": ["q1", "q2"],
            "query": ["binary positive relevance", "ignored non-positive relevance"],
        },
    )
    _ = Path(manifest.judgments_path).write_text(
        "\n".join(
            (
                "qid\tdocid\trelevance",
                "q1\td-positive-2\t2",
                "q1\td-positive-1\t1",
                "q1\td-zero\t0",
                "q1\td-negative\t-1",
                "q2\td-zero-only\t0",
                "q2\td-negative-only\t-2",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    selected_query_ids: list[str] = []

    class _Adapter:
        def run(
            self,
            *,
            manifest: DatasetManifest,
            level: LevelConfig,
            queries: tuple[BenchmarkQuery, ...],
        ) -> dict[str, object]:
            assert manifest.dataset_id == "beir_nq"
            assert level.level_id == "quick"
            selected_query_ids.extend(query.query_id for query in queries)
            return {
                "results": (
                    QueryResult(
                        query_id="q1",
                        ranked_doc_ids=(
                            "d-zero",
                            "d-positive-2",
                            "d-positive-1",
                            "d-negative",
                        ),
                        latency_ms=5.0,
                    ),
                )
            }

    monkeypatch.setattr(
        "snowiki.bench.runner.load_dataset_manifest", lambda path: manifest
    )
    monkeypatch.setattr("snowiki.bench.runner.get_target", lambda target_id: _Adapter())
    monkeypatch.setattr(
        "snowiki.bench.runner.resolve_dataset_assets",
        lambda manifest: {
            "corpus": tmp_path / "corpus.parquet",
            "queries": tmp_path / "queries.parquet",
            "judgments": tmp_path / "judgments.tsv",
        },
    )

    result = run_cell(
        matrix=matrix,
        dataset_id="beir_nq",
        level_id="quick",
        target_id="test_target",
    )

    expected_ndcg = ((1.0 / math.log2(3)) + (1.0 / math.log2(4))) / (
        1.0 + (1.0 / math.log2(3))
    )
    metric_by_id = {metric.metric_id: metric for metric in result.metrics}

    assert result.status == "success"
    assert selected_query_ids == ["q1"]
    assert result.details["eligible_query_count"] == 1
    assert result.details["effective_query_count"] == 1
    assert result.details["per_query"] == {
        "q1": {
            "ranked_doc_ids": ["d-zero", "d-positive-2", "d-positive-1", "d-negative"],
            "relevant_doc_ids": ["d-positive-1", "d-positive-2"],
            "latency_ms": 5.0,
            "metrics": {
                "recall_at_100": 1.0,
                "mrr_at_10": 0.5,
                "ndcg_at_10": pytest.approx(expected_ndcg),
                "latency_p50_ms": 5.0,
                "latency_p95_ms": 5.0,
            },
        }
    }
    assert metric_by_id["recall_at_100"].value == 1.0
    assert metric_by_id["mrr_at_10"].value == 0.5
    assert metric_by_id["ndcg_at_10"].value == pytest.approx(expected_ndcg)
    assert metric_by_id["latency_p50_ms"].value == 5.0
    assert metric_by_id["latency_p95_ms"].value == 5.0


def _write_parquet(path: Path, data: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = Dataset.from_dict(data)
    _ = dataset.to_parquet(path.as_posix())
