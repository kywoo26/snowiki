from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest
from datasets import Dataset

from snowiki.bench.cache import (
    BM25_CACHE_SCHEMA_VERSION,
    BM25_INDEX_FORMAT_VERSION,
    bm25_cache_paths,
    build_bm25_cache_identity,
    load_or_rebuild_bm25_cache,
)
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
from snowiki.storage.zones import StoragePaths


class _Adapter:
    def run(
        self,
        *,
        manifest: DatasetManifest,
        level: LevelConfig,
        queries: tuple[BenchmarkQuery, ...],
        include_diagnostics: bool = False,
    ) -> Mapping[str, object]:
        del manifest, level, queries, include_diagnostics
        return {}


def test_bm25_cache_identity_covers_ordered_corpus_tokenizer_and_versions() -> None:
    identity = build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture_dataset/corpus.parquet",
        corpus_hash="corpus-sha256",
        corpus_cap=50,
        documents=(("doc-b", "Beta text"), ("doc-a", "Alpha text")),
        tokenizer_name="regex_v1",
        tokenizer_config={"family": "regex", "lowercase": True},
        tokenizer_version=1,
        bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
    )
    corpus = cast(Mapping[str, object], identity["corpus"])
    documents = cast(Mapping[str, object], identity["documents"])
    tokenizer = cast(Mapping[str, object], identity["tokenizer"])
    bm25 = cast(Mapping[str, object], identity["bm25"])

    assert identity["target_name"] == "bm25_regex_v1"
    assert corpus["identity"] == "fixture_dataset/corpus.parquet"
    assert corpus["hash"] == "corpus-sha256"
    assert corpus["cap"] == 50
    assert documents["ordered_doc_ids"] == ["doc-b", "doc-a"]
    assert len(cast(str, documents["content_hash"])) == 64
    assert tokenizer["name"] == "regex_v1"
    assert tokenizer["config"] == {"family": "regex", "lowercase": True}
    assert tokenizer["version"] == 1
    assert bm25["params"] == {
        "b": 0.75,
        "delta": 0.5,
        "k1": 1.5,
        "method": "lucene",
    }
    assert identity["cache_schema_version"] == BM25_CACHE_SCHEMA_VERSION
    assert identity["index_format_version"] == BM25_INDEX_FORMAT_VERSION
    assert isinstance(bm25["package_version"], str)
    assert len(cast(str, identity["identity_hash"])) == 64

    reordered_identity = build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture_dataset/corpus.parquet",
        corpus_hash="corpus-sha256",
        corpus_cap=50,
        documents=(("doc-a", "Alpha text"), ("doc-b", "Beta text")),
        tokenizer_name="regex_v1",
        tokenizer_config={"family": "regex", "lowercase": True},
        tokenizer_version=1,
        bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
    )
    tokenizer_changed_identity = build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture_dataset/corpus.parquet",
        corpus_hash="corpus-sha256",
        corpus_cap=50,
        documents=(("doc-b", "Beta text"), ("doc-a", "Alpha text")),
        tokenizer_name="regex_v1",
        tokenizer_config={"family": "regex", "lowercase": True},
        tokenizer_version=2,
        bm25_params={"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5},
    )

    assert reordered_identity["identity_hash"] != identity["identity_hash"]
    assert tokenizer_changed_identity["identity_hash"] != identity["identity_hash"]


def test_bm25_wordpiece_cache_identity_includes_training_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from snowiki import benchmark_targets

    monkeypatch.setattr(
        benchmark_targets,
        "resolve_dataset_assets",
        lambda _manifest, *, level_id: {"corpus": Path("fixture/corpus.json")},
    )
    monkeypatch.setattr(
        benchmark_targets,
        "_sha256_file",
        lambda _path: "corpus-sha256",
    )
    adapter = benchmark_targets._BM25TargetAdapter(
        "bm25_hf_wordpiece_v1",
        "hf_wordpiece_v1",
    )
    manifest = DatasetManifest(
        dataset_id="fixture",
        name="Fixture",
        language="en",
        purpose_tags=("unit",),
        corpus_path="corpus.json",
        queries_path="queries.json",
        judgments_path="judgments.json",
        field_mappings={},
        supported_levels=("tiny",),
    )
    level = LevelConfig(level_id="tiny", query_cap=1)

    identity = adapter._cache_identity(
        manifest=manifest,
        level=level,
        corpus_rows=(("doc-a", "Alpha text"),),
    )

    tokenizer = cast(Mapping[str, object], identity["tokenizer"])
    config = cast(Mapping[str, object], tokenizer["config"])
    assert config == {
        "family": "subword",
        "lowercase": True,
        "min_frequency": 1,
        "runtime_supported": False,
        "vocab_size": 30000,
    }


@pytest.mark.parametrize(
    "changed_field",
    ["corpus_cap", "document_content", "tokenizer_name", "tokenizer_config", "bm25_params"],
)
def test_bm25_cache_rebuilds_when_identity_dimensions_change(
    tmp_path: Path,
    changed_field: str,
) -> None:
    storage_paths = StoragePaths(tmp_path / "runtime")
    seeded_identity = _cache_identity_variant()
    changed_identity = _cache_identity_variant(changed_field)
    builds: list[str] = []

    seeded = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=seeded_identity,
        build_artifact=lambda: _built_cache_artifact(builds, b"seed"),
        load_artifact=lambda path: path.read_bytes(),
    )
    changed = load_or_rebuild_bm25_cache(
        storage_paths=storage_paths,
        identity=changed_identity,
        build_artifact=lambda: _built_cache_artifact(builds, changed_field.encode()),
        load_artifact=lambda path: path.read_bytes(),
    )

    assert seeded.metadata["cache_status"] == "rebuilt"
    assert changed.value == changed_field.encode()
    assert changed.metadata["cache_hit"] is False
    assert changed.metadata["cache_status"] == "rebuilt"
    assert changed.metadata["cache_miss_reason"] == "missing_manifest"
    assert changed.metadata["cache_rebuilt"] is True
    assert builds == ["built", "built"]


def _cache_identity_variant(changed_field: str | None = None) -> dict[str, object]:
    corpus_cap = 75 if changed_field == "corpus_cap" else 50
    documents = (
        (("doc-a", "Alpha text changed"),)
        if changed_field == "document_content"
        else (("doc-a", "Alpha text"),)
    )
    tokenizer_name = (
        "kiwi_morphology_v1" if changed_field == "tokenizer_name" else "regex_v1"
    )
    tokenizer_config = (
        {"family": "regex", "lowercase": False}
        if changed_field == "tokenizer_config"
        else {"family": "regex", "lowercase": True}
    )
    bm25_params = (
        {"method": "lucene", "k1": 1.2, "b": 0.75, "delta": 0.5}
        if changed_field == "bm25_params"
        else {"method": "lucene", "k1": 1.5, "b": 0.75, "delta": 0.5}
    )
    return build_bm25_cache_identity(
        target_name="bm25_regex_v1",
        corpus_identity="fixture_dataset/corpus.parquet",
        corpus_hash="corpus-sha256",
        corpus_cap=corpus_cap,
        documents=documents,
        tokenizer_name=tokenizer_name,
        tokenizer_config=tokenizer_config,
        tokenizer_version=1,
        bm25_params=bm25_params,
    )


def test_bm25_cache_paths_use_snowiki_runtime_index_zone(tmp_path: Path) -> None:
    paths = StoragePaths(tmp_path / "runtime")

    cache_paths = bm25_cache_paths(
        storage_paths=paths,
        target_name="bm25 regex/v1",
        identity_hash="abc123",
    )

    assert cache_paths.root == paths.index / "bench" / "bm25" / "bm25-regex-v1" / "abc123"
    assert cache_paths.manifest_path == cache_paths.root / "manifest.json"
    assert cache_paths.artifact_path == cache_paths.root / "index.bm25cache"
    assert not cache_paths.root.as_posix().startswith("benchmarks/")


def test_builtin_targets_are_discoverable() -> None:
    expected_ids = {
        "snowiki_query_runtime_v1",
        "bm25_regex_v1",
        "bm25_kiwi_morphology_v1",
        "bm25_kiwi_nouns_v1",
        "bm25_mecab_morphology_v1",
        "bm25_hf_wordpiece_v1",
    }
    expected_datasets = (
        "beir_nq",
        "beir_scifact",
        "trec_dl_2020_passage",
        "miracl_ko",
        "snowiki_retrieval_regression",
    )

    assert len(BUILTIN_TARGETS) == 6
    assert {spec.target_id for spec in BUILTIN_TARGETS} == expected_ids
    assert {spec.target_id for spec in DEFAULT_TARGET_REGISTRY.list_targets()} == expected_ids
    for spec in BUILTIN_TARGETS:
        assert spec.supported_datasets == expected_datasets


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


def test_snowiki_query_runtime_target_executes_topical_policy(tmp_path: Path) -> None:
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        _level_asset_path(manifest.corpus_path),
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
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-b\t1\n",
        encoding="utf-8",
    )

    execution = DEFAULT_TARGET_REGISTRY.get_target("snowiki_query_runtime_v1").run(
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
    assert "cache" not in execution


def test_bm25_regex_target_executes_on_tiny_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        _level_asset_path(manifest.corpus_path),
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
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-b\t1\n",
        encoding="utf-8",
    )

    execution = DEFAULT_TARGET_REGISTRY.get_target("bm25_regex_v1").run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1),
        queries=(BenchmarkQuery(query_id="q1", query_text="needle alpha"),),
        include_diagnostics=True,
    )

    results = tuple(cast(QueryResult, result) for result in execution["results"])
    cache = cast(Mapping[str, object], execution["cache"])

    assert len(results) == 1
    assert results[0].query_id == "q1"
    assert results[0].ranked_doc_ids[:2] == ("doc-b", "doc-c")
    assert results[0].latency_ms is not None
    assert (results[0].latency_ms or 0.0) >= 0.0
    diagnostics = results[0].diagnostics
    assert diagnostics["retriever"] == "bm25"
    assert diagnostics["tokenizer"] == "regex_v1"
    assert diagnostics["query_tokens"] == ["needle alpha", "needle", "alpha"]
    top_hits = cast(list[Mapping[str, object]], diagnostics["top_hits"])
    assert top_hits[0]["rank"] == 1
    assert top_hits[0]["doc_id"] == "doc-b"
    assert isinstance(top_hits[0]["score"], float)
    assert top_hits[0]["matched_terms"] == ["needle", "alpha"]
    assert set(cast(list[str], top_hits[0]["document_tokens"])).issuperset(
        {"needle", "alpha", "phrase"}
    )
    assert cast(Mapping[str, object], top_hits[0]["document"])["path"] == "doc-b"
    token_overlap = cast(Mapping[str, object], top_hits[0]["token_overlap"])
    assert token_overlap["matched_query_token_count"] == 2
    assert cache["cache_hit"] is False
    assert cache["cache_status"] == "rebuilt"
    assert cache["cache_miss_reason"] == "missing_manifest"
    assert cache["cache_rebuilt"] is True
    assert cache["cache_schema_version"] == BM25_CACHE_SCHEMA_VERSION
    assert cast(float, cache["index_build_seconds"]) >= 0.0
    assert Path(cast(str, cache["cache_manifest_path"])).is_file()


def test_bm25_target_hits_persistent_cache_and_skips_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_cache_fixture_files(manifest)
    builds: list[float] = []
    loads: list[Path] = []
    matched_term_flags: list[bool] = []

    class _FakeHit:
        def __init__(self, document: object) -> None:
            self.document = document
            self.score = 1.0
            self.matched_terms = ("alpha",)

    class _FakeIndex:
        def __init__(self, documents: Sequence[object], tokenizer_name: str) -> None:
            assert tokenizer_name == "regex_v1"
            builds.append(time.perf_counter())
            self.documents = list(documents)
            self.tokenizer_name = tokenizer_name

        def to_cache_bytes(self) -> bytes:
            return b"fake-bm25-index"

        @classmethod
        def load_cache_artifact(
            cls,
            path: Path,
            documents: Sequence[object],
            *,
            expected_tokenizer_name: str | None = None,
            load_corpus_tokens: bool = False,
        ) -> object:
            assert expected_tokenizer_name == "regex_v1"
            assert load_corpus_tokens is False
            assert path.read_bytes() == b"fake-bm25-index"
            loads.append(path)
            instance = cls.__new__(cls)
            instance.documents = list(documents)
            instance.tokenizer_name = expected_tokenizer_name or "regex_v1"
            return instance

        def search(
            self,
            query: str,
            limit: int = 10,
            *,
            include_matched_terms: bool = True,
        ) -> list[_FakeHit]:
            del query, limit
            matched_term_flags.append(include_matched_terms)
            return [_FakeHit(self.documents[0])]

        def tokenize_query(self, query: str) -> tuple[str, ...]:
            del query
            return ("alpha",)

        def tokens_for_document(self, document_id: str) -> tuple[str, ...]:
            del document_id
            return ("alpha", "cache", "hit")

    monkeypatch.setattr(
        "snowiki.benchmark_targets._load_materialized_corpus_rows",
        lambda manifest, *, level: (("doc-a", "alpha cache hit"),),
    )
    monkeypatch.setattr("snowiki.benchmark_targets.BM25SearchIndex", _FakeIndex)

    target = DEFAULT_TARGET_REGISTRY.get_target("bm25_regex_v1")
    query = BenchmarkQuery(query_id="q1", query_text="alpha")
    start_first = time.perf_counter()
    first = target.run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=10),
        queries=(query,),
    )
    first_seconds = time.perf_counter() - start_first
    start_second = time.perf_counter()
    second = target.run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=10),
        queries=(query,),
    )
    second_seconds = time.perf_counter() - start_second

    first_cache = cast(Mapping[str, object], first["cache"])
    second_cache = cast(Mapping[str, object], second["cache"])

    assert first_cache["cache_hit"] is False
    assert first_cache["cache_status"] == "rebuilt"
    assert first_cache["cache_miss_reason"] == "missing_manifest"
    assert first_cache["cache_rebuilt"] is True
    assert cast(float, first_cache["index_build_seconds"]) >= 0.0
    assert second_cache["cache_hit"] is True
    assert second_cache["cache_status"] == "hit"
    assert second_cache["cache_miss_reason"] is None
    assert second_cache["cache_rebuilt"] is False
    assert second_cache["index_build_seconds"] == 0.0
    assert builds == [builds[0]]
    assert len(loads) == 1
    assert matched_term_flags == [False, False]
    # Timing comparison is intentionally loose; CI runners can be very fast.
    # The behavioural assertions above (single build, single load, cache_hit=True)
    # are the real correctness check.
    assert second_seconds <= first_seconds


def test_bm25_target_rebuilds_and_reports_corrupt_cached_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_cache_fixture_files(manifest)
    builds: list[str] = []
    load_attempts: list[Path] = []

    class _FakeIndex:
        def __init__(self, documents: Sequence[object], tokenizer_name: str) -> None:
            builds.append("built")
            self.documents = list(documents)
            self.tokenizer_name = tokenizer_name

        def to_cache_bytes(self) -> bytes:
            return b"fake-bm25-index"

        @classmethod
        def load_cache_artifact(
            cls,
            path: Path,
            documents: Sequence[object],
            *,
            expected_tokenizer_name: str | None = None,
            load_corpus_tokens: bool = False,
        ) -> object:
            del documents, expected_tokenizer_name, load_corpus_tokens
            load_attempts.append(path)
            raise ValueError("cached index is corrupt")

        def search(
            self,
            query: str,
            limit: int = 10,
            *,
            include_matched_terms: bool = True,
        ) -> list[object]:
            del query, limit, include_matched_terms
            return []

        def tokenize_query(self, query: str) -> tuple[str, ...]:
            del query
            return ("alpha",)

    monkeypatch.setattr(
        "snowiki.benchmark_targets._load_materialized_corpus_rows",
        lambda manifest, *, level: (("doc-a", "alpha cache corrupt"),),
    )
    monkeypatch.setattr("snowiki.benchmark_targets.BM25SearchIndex", _FakeIndex)
    target = DEFAULT_TARGET_REGISTRY.get_target("bm25_regex_v1")
    query = BenchmarkQuery(query_id="q1", query_text="alpha")
    _ = target.run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1),
        queries=(query,),
    )

    second = target.run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1),
        queries=(query,),
    )

    cache = cast(Mapping[str, object], second["cache"])
    assert cache["cache_hit"] is False
    assert cache["cache_status"] == "rebuilt"
    assert cache["cache_miss_reason"] == "corrupt_load"
    assert cache["cache_rebuilt"] is True
    assert builds == ["built", "built"]
    assert len(load_attempts) == 1


def test_builtin_targets_are_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    corpus_path = tmp_path / "corpus.parquet"
    queries_path = tmp_path / "queries.parquet"
    judgments_path = tmp_path / "judgments.tsv"

    _write_parquet(
        _level_asset_path(corpus_path.as_posix()),
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
        if spec.target_id == "snowiki_query_runtime_v1":
            assert "cache" not in execution
        else:
            cache = cast(Mapping[str, object], execution["cache"])
            assert cache["cache_schema_version"] == BM25_CACHE_SCHEMA_VERSION
            assert "index_build_seconds" in cache


def test_corpus_sampling_keeps_all_judged_docs_before_random_fill(
    tmp_path: Path,
) -> None:
    import snowiki.benchmark_targets as benchmark_targets

    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        _level_asset_path(manifest.corpus_path),
        rows=[
            {"docid": "doc-a", "text": "alpha"},
            {"docid": "doc-b", "text": "beta"},
            {"docid": "doc-c", "text": "gamma"},
            {"docid": "doc-d", "text": "delta"},
            {"docid": "doc-e", "text": "epsilon"},
        ],
        columns=("docid", "text"),
    )
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-c\t1\nq2\tdoc-e\t1\n",
        encoding="utf-8",
    )

    sampled_rows = benchmark_targets._load_materialized_corpus_rows(
        manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=4),
    )

    sampled_doc_ids = tuple(doc_id for doc_id, _ in sampled_rows)
    assert sampled_doc_ids[:2] == ("doc-c", "doc-e")
    assert len(sampled_doc_ids) == 4
    assert set(sampled_doc_ids[2:]).issubset({"doc-a", "doc-b", "doc-d"})


def test_corpus_sampling_treats_cap_as_minimum_for_judged_docs(tmp_path: Path) -> None:
    import snowiki.benchmark_targets as benchmark_targets

    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        _level_asset_path(manifest.corpus_path),
        rows=[
            {"docid": "doc-a", "text": "alpha"},
            {"docid": "doc-b", "text": "beta"},
            {"docid": "doc-c", "text": "gamma"},
        ],
        columns=("docid", "text"),
    )
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-a\t1\nq2\tdoc-c\t1\n",
        encoding="utf-8",
    )

    sampled_rows = benchmark_targets._load_materialized_corpus_rows(
        manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=1),
    )

    assert tuple(doc_id for doc_id, _ in sampled_rows) == ("doc-a", "doc-c")


def test_corpus_sampling_preserves_order_when_corpus_fits_cap(tmp_path: Path) -> None:
    import snowiki.benchmark_targets as benchmark_targets

    manifest = _materialized_fixture_manifest(tmp_path)
    _write_parquet(
        _level_asset_path(manifest.corpus_path),
        rows=[
            {"docid": "doc-a", "text": "alpha"},
            {"docid": "doc-b", "text": "beta"},
            {"docid": "doc-c", "text": "gamma"},
        ],
        columns=("docid", "text"),
    )
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-c\t1\n",
        encoding="utf-8",
    )

    sampled_rows = benchmark_targets._load_materialized_corpus_rows(
        manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=10),
    )

    assert tuple(doc_id for doc_id, _ in sampled_rows) == ("doc-a", "doc-b", "doc-c")


def test_json_corpus_loader_reads_wrapped_corpus_rows(tmp_path: Path) -> None:
    import snowiki.benchmark_targets as benchmark_targets

    corpus_path = tmp_path / "corpus.json"
    level_corpus_path = tmp_path / "regression" / "corpus.json"
    level_corpus_path.parent.mkdir(parents=True, exist_ok=True)
    level_corpus_path.write_text(
        '{"corpus": [{"docid": "doc-a", "text": "alpha"}, {"docid": "doc-b", "text": "beta"}]}\n',
        encoding="utf-8",
    )
    manifest = _json_fixture_manifest(corpus_path)

    rows = benchmark_targets._load_materialized_corpus_rows(
        manifest,
        level=LevelConfig(level_id="regression", query_cap=2),
    )

    assert rows == (("doc-a", "alpha"), ("doc-b", "beta"))


def test_json_corpus_loader_reads_top_level_rows(tmp_path: Path) -> None:
    import snowiki.benchmark_targets as benchmark_targets

    corpus_path = tmp_path / "corpus.json"
    level_corpus_path = tmp_path / "regression" / "corpus.json"
    level_corpus_path.parent.mkdir(parents=True, exist_ok=True)
    level_corpus_path.write_text(
        '[{"docid": "doc-a", "text": "alpha"}, {"docid": "doc-b", "text": "beta"}]\n',
        encoding="utf-8",
    )
    manifest = _json_fixture_manifest(corpus_path)

    rows = benchmark_targets._load_materialized_corpus_rows(
        manifest,
        level=LevelConfig(level_id="regression", query_cap=2, corpus_cap=1),
    )

    assert rows == (("doc-a", "alpha"),)


def test_bm25_target_uses_level_corpus_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SNOWIKI_ROOT", (tmp_path / "runtime").as_posix())
    manifest = _materialized_fixture_manifest(tmp_path)
    _write_cache_fixture_files(manifest)
    received_levels: list[LevelConfig] = []

    def _load_rows(
        manifest: DatasetManifest,
        *,
        level: LevelConfig,
    ) -> tuple[tuple[str, str], ...]:
        del manifest
        received_levels.append(level)
        return (("doc-a", "alpha"),)

    class _FakeIndex:
        def __init__(self, documents: Sequence[object], tokenizer_name: str) -> None:
            del documents
            self.tokenizer_name = tokenizer_name

        def to_cache_bytes(self) -> bytes:
            return b"fake-bm25-index"

        def search(
            self,
            query: str,
            limit: int = 10,
            *,
            include_matched_terms: bool = True,
        ) -> list[object]:
            del query, limit, include_matched_terms
            return []

        def tokenize_query(self, query: str) -> tuple[str, ...]:
            del query
            return ("alpha",)

    monkeypatch.setattr("snowiki.benchmark_targets._load_materialized_corpus_rows", _load_rows)
    monkeypatch.setattr("snowiki.benchmark_targets.BM25SearchIndex", _FakeIndex)

    _ = DEFAULT_TARGET_REGISTRY.get_target("bm25_regex_v1").run(
        manifest=manifest,
        level=LevelConfig(level_id="quick", query_cap=1, corpus_cap=50),
        queries=(BenchmarkQuery(query_id="q1", query_text="alpha"),),
    )

    assert [level.corpus_cap for level in received_levels] == [50]


def _built_cache_artifact(builds: list[str], content: bytes) -> tuple[bytes, bytes]:
    builds.append("built")
    return content, content


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


def _json_fixture_manifest(corpus_path: Path) -> DatasetManifest:
    return DatasetManifest(
        dataset_id="json_fixture",
        name="JSON Fixture Dataset",
        language="en",
        purpose_tags=("product-regression",),
        corpus_path=corpus_path.as_posix(),
        queries_path=(corpus_path.parent / "queries.json").as_posix(),
        judgments_path=(corpus_path.parent / "judgments.json").as_posix(),
        field_mappings={},
        supported_levels=("regression",),
    )


def _level_asset_path(raw_path: str, level_id: str = "quick") -> Path:
    path = Path(raw_path)
    return path.parent / level_id / path.name


def _write_cache_fixture_files(manifest: DatasetManifest) -> None:
    corpus_path = _level_asset_path(manifest.corpus_path)
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_bytes(b"cache fixture corpus")
    _ = _level_asset_path(manifest.judgments_path).write_text(
        "qid\tdocid\trelevance\nq1\tdoc-a\t1\n",
        encoding="utf-8",
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
