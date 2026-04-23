from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest
from datasets import Dataset

from snowiki.bench.specs import (
    BenchmarkQuery,
    BenchmarkTargetSpec,
    DatasetManifest,
    LevelConfig,
    QueryResult,
)
from snowiki.bench.targets import (
    BUILTIN_TARGETS,
    DEFAULT_TARGET_REGISTRY,
    TargetRegistry,
)


class _Adapter:
    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
    ) -> Mapping[str, object]:
        del manifest, level, queries
        return {}


def test_builtin_targets_are_discoverable() -> None:
    expected_ids = {
        "lexical_regex_v1",
        "bm25_regex_v1",
        "bm25_kiwi_morphology_v1",
        "bm25_kiwi_nouns_v1",
        "bm25_mecab_morphology_v1",
        "bm25_hf_wordpiece_v1",
    }

    assert len(BUILTIN_TARGETS) == 6
    assert {spec.target_id for spec in BUILTIN_TARGETS} == expected_ids
    assert {spec.target_id for spec in DEFAULT_TARGET_REGISTRY.list_targets()} == expected_ids


def test_unknown_target_raises_clear_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark target: missing_target"):
        _ = DEFAULT_TARGET_REGISTRY.get_target("missing_target")


def test_duplicate_registration_raises_value_error() -> None:
    registry = TargetRegistry()
    spec = BenchmarkTargetSpec(target_id="duplicate_target")
    adapter = _Adapter()

    registry.register_target(spec, adapter)

    with pytest.raises(ValueError, match="Target already registered: duplicate_target"):
        registry.register_target(spec, adapter)


def test_lexical_regex_target_executes_on_tiny_fixture(tmp_path: Path) -> None:
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        Path(manifest.corpus_path),
        rows=[
            {"docid": "doc-a", "text": "alpha topic"},
            {"docid": "doc-b", "text": "needle alpha phrase"},
            {"docid": "doc-c", "text": "needle only"},
        ],
        columns=("docid", "text"),
    )
    _write_parquet(
        Path(manifest.queries_path),
        rows=[{"qid": "q1", "query": "needle alpha"}],
        columns=("qid", "query"),
    )
    _ = Path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-b\t1\n",
        encoding="utf-8",
    )

    execution = DEFAULT_TARGET_REGISTRY.get_target("lexical_regex_v1").run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1),
        queries=(BenchmarkQuery(query_id="q1", query_text="needle alpha"),),
    )

    results = tuple(cast(QueryResult, result) for result in execution["results"])

    assert len(results) == 1
    assert results[0].query_id == "q1"
    assert results[0].ranked_doc_ids[0] == "doc-b"
    assert set(results[0].ranked_doc_ids[:3]) == {"doc-a", "doc-b", "doc-c"}
    assert results[0].latency_ms is not None
    assert (results[0].latency_ms or 0.0) >= 0.0


def test_bm25_regex_target_executes_on_tiny_fixture(tmp_path: Path) -> None:
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        Path(manifest.corpus_path),
        rows=[
            {"docid": "doc-a", "text": "alpha topic"},
            {"docid": "doc-b", "text": "needle alpha phrase"},
            {"docid": "doc-c", "text": "needle only"},
        ],
        columns=("docid", "text"),
    )
    _write_parquet(
        Path(manifest.queries_path),
        rows=[{"qid": "q1", "query": "needle alpha"}],
        columns=("qid", "query"),
    )
    _ = Path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-b\t1\n",
        encoding="utf-8",
    )

    execution = DEFAULT_TARGET_REGISTRY.get_target("bm25_regex_v1").run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1),
        queries=(BenchmarkQuery(query_id="q1", query_text="needle alpha"),),
    )

    results = tuple(cast(QueryResult, result) for result in execution["results"])

    assert len(results) == 1
    assert results[0].query_id == "q1"
    assert results[0].ranked_doc_ids[:2] == ("doc-b", "doc-c")
    assert results[0].latency_ms is not None
    assert (results[0].latency_ms or 0.0) >= 0.0


def test_builtin_targets_are_executable(tmp_path: Path) -> None:
    corpus_path = tmp_path / "corpus.parquet"
    queries_path = tmp_path / "queries.parquet"
    judgments_path = tmp_path / "judgments.tsv"

    _write_parquet(
        corpus_path,
        rows=[
            {"docid": f"doc{i}", "text": f"common token document {i}"}
            for i in range(104)
        ]
        + [{"docid": "doc104", "text": "common token needle document 104"}],
        columns=("docid", "text"),
    )
    _write_parquet(
        queries_path,
        rows=[{"qid": "q1", "query": "common"}, {"qid": "q2", "query": "needle"}],
        columns=("qid", "query"),
    )
    _ = judgments_path.write_text("qid\tdocid\trelevance\n", encoding="utf-8")

    manifest = DatasetManifest(
        dataset_id="fixture_dataset",
        name="Fixture Dataset",
        language="en",
        purpose_tags=("passage-retrieval",),
        corpus_path=corpus_path.as_posix(),
        queries_path=queries_path.as_posix(),
        judgments_path=judgments_path.as_posix(),
        field_mappings={},
        supported_levels=("quick",),
    )
    queries = (
        BenchmarkQuery(query_id="q1", query_text="common"),
        BenchmarkQuery(query_id="q2", query_text="needle"),
    )
    level = LevelConfig(level_id="quick", query_cap=2)

    for spec in BUILTIN_TARGETS:
        execution = DEFAULT_TARGET_REGISTRY.get_target(spec.target_id).run(
            manifest=manifest,
            level=level,
            queries=queries,
        )

        raw_results = execution["results"]

        assert isinstance(raw_results, tuple)
        assert all(isinstance(result, QueryResult) for result in raw_results)
        results = tuple(cast(QueryResult, result) for result in raw_results)
        assert tuple(result.query_id for result in results) == ("q1", "q2")
        assert results[0].ranked_doc_ids
        assert len(results[0].ranked_doc_ids) == 100
        assert "doc104" in results[1].ranked_doc_ids
        assert all(result.latency_ms is not None for result in results)
        assert all((result.latency_ms or 0.0) >= 0.0 for result in results)


def _materialized_fixture_manifest(tmp_path: Path) -> DatasetManifest:
    materialized_dir = tmp_path / "materialized"
    return DatasetManifest(
        dataset_id="fixture_dataset",
        name="Fixture Dataset",
        language="en",
        purpose_tags=("passage-retrieval",),
        corpus_path=(materialized_dir / "corpus.parquet").as_posix(),
        queries_path=(materialized_dir / "queries.parquet").as_posix(),
        judgments_path=(materialized_dir / "judgments.tsv").as_posix(),
        field_mappings={},
        supported_levels=("quick",),
    )


def _write_parquet(
    path: Path,
    *,
    rows: Sequence[Mapping[str, object]],
    columns: tuple[str, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset = Dataset.from_dict(
        {column: [row[column] for row in rows] for column in columns}
    )
    _ = dataset.to_parquet(path.as_posix())
