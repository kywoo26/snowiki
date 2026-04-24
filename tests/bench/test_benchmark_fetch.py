from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest
from click.testing import CliRunner
from datasets import load_dataset as load_local_dataset

import snowiki.benchmark_fetch as benchmark_fetch
from snowiki.bench.specs import DatasetManifest, LevelConfig
from snowiki.cli.main import app


def test_materialize_dataset_writes_normalized_outputs_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact")
    calls: list[tuple[str, str, str, str, str, bool]] = []

    def fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> Sequence[Mapping[str, object]]:
        calls.append((repo_id, config, split, revision, cache_dir, streaming))
        fixtures = {
            ("example/scifact", "corpus", "corpus"): [
                {"_id": "d1", "text": "doc one"},
                {"_id": "d2", "content": "doc two"},
                {"_id": "d3", "text": "", "title": "doc three title"},
                {"_id": "d4", "text": "doc four"},
            ],
            ("example/scifact", "queries", "queries"): [
                {"_id": "q1", "text": "what is scifact?"},
            ],
            ("example/scifact-qrels", "default", "test"): [
                {"query-id": "q1", "corpus-id": "d2", "score": 2},
                {"query-id": "q1", "corpus-id": "d3", "score": 0},
                {"query-id": "q1", "corpus-id": "d4", "score": -1},
            ],
        }
        return fixtures[(repo_id, config, split)]

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fake_load_dataset)

    result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())

    assert result["action"] == "materialize"
    assert [call[:4] for call in calls] == [
        ("example/scifact", "queries", "queries", "queries-sha"),
        ("example/scifact-qrels", "default", "test", "judgments-sha"),
        ("example/scifact", "corpus", "corpus", "corpus-sha"),
    ]
    assert all(call[4] == (tmp_path / "benchmarks/hf").as_posix() for call in calls)
    assert [call[5] for call in calls] == [False, False, True]

    materialized_dir = tmp_path / "benchmarks/materialized/beir_scifact/quick"
    corpus = load_local_dataset(
        "parquet",
        data_files=(materialized_dir / "corpus.parquet").as_posix(),
        split="train",
    )
    queries = load_local_dataset(
        "parquet",
        data_files=(materialized_dir / "queries.parquet").as_posix(),
        split="train",
    )

    assert corpus.column_names == ["docid", "text"]
    assert corpus[:4] == {
        "docid": ["d2", "d3", "d4", "d1"],
        "text": ["doc two", "doc three title", "doc four", "doc one"],
    }
    assert queries.column_names == ["qid", "query"]
    assert queries[:1] == {"qid": ["q1"], "query": ["what is scifact?"]}
    assert (materialized_dir / "judgments.tsv").read_text(encoding="utf-8") == (
        "qid\tdocid\trelevance\nq1\td2\t2\nq1\td3\t0\nq1\td4\t-1\n"
    )

    sidecar = cast(
        dict[str, object],
        json.loads((materialized_dir / "materialization.json").read_text(encoding="utf-8")),
    )
    source_locators = cast(dict[str, dict[str, str]], sidecar["source_locators"])
    resolved_revisions = cast(dict[str, str], sidecar["resolved_revisions"])
    row_counts = cast(dict[str, int], sidecar["row_counts"])
    materialization_config = cast(dict[str, object], sidecar["materialization_config"])
    timestamps = cast(dict[str, str], sidecar["timestamps"])

    assert source_locators["corpus"] == {
        "repo_id": "example/scifact",
        "config": "corpus",
        "split": "corpus",
        "revision": "corpus-sha",
    }
    assert resolved_revisions == {
        "corpus": "corpus-sha",
        "queries": "queries-sha",
        "judgments": "judgments-sha",
    }
    assert row_counts == {"corpus": 4, "queries": 1, "judgments": 3}
    assert materialization_config["level_id"] == "quick"
    assert materialization_config["query_cap"] == 10
    assert materialization_config["corpus_cap"] == 10
    assert set(timestamps) == {"started_at", "completed_at"}


def test_materialize_dataset_passes_trust_remote_code_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact", trust_remote_code=True)
    calls: list[bool] = []

    def fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> Sequence[Mapping[str, object]]:
        del repo_id, config, revision, cache_dir, streaming
        calls.append(trust_remote_code)
        rows_by_split: dict[str, Sequence[Mapping[str, object]]] = {
            "corpus": [{"_id": "d1", "text": "doc one"}],
            "queries": [{"_id": "q1", "text": "query one"}],
            "test": [{"query-id": "q1", "corpus-id": "d1", "score": 1}],
        }
        return rows_by_split[split]

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fake_load_dataset)

    result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())

    assert result["action"] == "materialize"
    assert calls == [True, True, True]
    sidecar = cast(
        dict[str, object],
        json.loads(
            (
                tmp_path
                / "benchmarks/materialized/beir_scifact/quick/materialization.json"
            ).read_text(encoding="utf-8")
        ),
    )
    source_locators = cast(dict[str, dict[str, object]], sidecar["source_locators"])
    assert source_locators["corpus"]["trust_remote_code"] is True


def test_materialize_dataset_skips_when_sidecar_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact")
    load_calls = 0

    def fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> Sequence[Mapping[str, object]]:
        nonlocal load_calls
        load_calls += 1
        fixtures = {
            ("example/scifact", "corpus", "corpus"): [{"_id": "d1", "text": "doc one"}],
            ("example/scifact", "queries", "queries"): [{"_id": "q1", "text": "query one"}],
            ("example/scifact-qrels", "default", "test"): [
                {"query-id": "q1", "corpus-id": "d1", "score": 1},
            ],
        }
        return fixtures[(repo_id, config, split)]

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fake_load_dataset)

    first_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())
    second_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())

    assert first_result["action"] == "materialize"
    assert second_result == {
        "dataset_id": "beir_scifact",
        "level_id": "quick",
        "action": "skip",
        "reason": "cache_hit",
        "dry_run": False,
        "output_dir": tmp_path / "benchmarks/materialized/beir_scifact/quick",
        "sidecar_path": tmp_path
        / "benchmarks/materialized/beir_scifact/quick/materialization.json",
    }
    assert load_calls == 3


def test_materialize_dataset_re_materializes_when_source_locators_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact")
    calls: list[tuple[str, str, str, str]] = []

    def fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> Sequence[Mapping[str, object]]:
        del cache_dir, streaming
        calls.append((repo_id, config, split, revision))
        fixtures = {
            ("example/scifact", "corpus", "corpus", "corpus-sha"): [
                {"_id": "d1", "text": "doc one"}
            ],
            ("example/scifact", "queries", "queries", "queries-sha"): [
                {"_id": "q1", "text": "query one"}
            ],
            ("example/scifact-qrels", "default", "test", "judgments-sha"): [
                {"query-id": "q1", "corpus-id": "d1", "score": 1}
            ],
            ("example/scifact", "corpus", "corpus", "corpus-sha-2"): [
                {"_id": "d1", "text": "doc one updated"}
            ],
        }
        return fixtures[(repo_id, config, split, revision)]

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fake_load_dataset)

    first_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())
    _write_manifest(
        tmp_path,
        dataset_id="beir_scifact",
        corpus_revision="corpus-sha-2",
    )
    second_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())

    assert first_result["action"] == "materialize"
    assert second_result["action"] == "materialize"
    assert second_result["reason"] == "source_locators_changed"
    assert calls == [
        ("example/scifact", "queries", "queries", "queries-sha"),
        ("example/scifact-qrels", "default", "test", "judgments-sha"),
        ("example/scifact", "corpus", "corpus", "corpus-sha"),
        ("example/scifact", "queries", "queries", "queries-sha"),
        ("example/scifact-qrels", "default", "test", "judgments-sha"),
        ("example/scifact", "corpus", "corpus", "corpus-sha-2"),
    ]
    sidecar = cast(
        dict[str, object],
        json.loads(
            (
                tmp_path
                / "benchmarks/materialized/beir_scifact/quick/materialization.json"
            ).read_text(encoding="utf-8")
        ),
    )
    resolved_revisions = cast(dict[str, str], sidecar["resolved_revisions"])
    assert resolved_revisions["corpus"] == "corpus-sha-2"


def test_materialize_dataset_re_materializes_when_field_mappings_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact")
    calls: list[tuple[str, str, str, str]] = []

    def fake_load_dataset(
        repo_id: str,
        config: str,
        *,
        split: str,
        revision: str,
        cache_dir: str,
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> Sequence[Mapping[str, object]]:
        del cache_dir, streaming
        calls.append((repo_id, config, split, revision))
        fixtures = {
            ("example/scifact", "corpus", "corpus", "corpus-sha"): [
                {"_id": "d1", "text": "doc one"}
            ],
            ("example/scifact", "queries", "queries", "queries-sha"): [
                {"_id": "q1", "text": "query one", "body": "query one body"}
            ],
            ("example/scifact-qrels", "default", "test", "judgments-sha"): [
                {"query-id": "q1", "corpus-id": "d1", "score": 1}
            ],
        }
        return fixtures[(repo_id, config, split, revision)]

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fake_load_dataset)

    first_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())
    _write_manifest_with_query_text_keys(
        tmp_path,
        dataset_id="beir_scifact",
        query_text_keys=("body", "text"),
    )
    second_result = benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())

    assert first_result["action"] == "materialize"
    assert second_result["action"] == "materialize"
    assert second_result["reason"] == "field_mappings_changed"
    assert len(calls) == 6
    queries = load_local_dataset(
        "parquet",
        data_files=(tmp_path / "benchmarks/materialized/beir_scifact/quick/queries.parquet").as_posix(),
        split="train",
    )
    assert queries[:1] == {"qid": ["q1"], "query": ["query one body"]}


def test_benchmark_fetch_cli_dry_run_reports_planned_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(tmp_path, dataset_id="beir_scifact")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run should not fetch datasets")

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "resolve_dataset_assets", _asset_resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fail_if_called)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["benchmark-fetch", "--dataset", "beir_scifact", "--level", "quick", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert result.output == (
        "dataset=beir_scifact level=quick plan=materialize reason=missing_sidecar "
        f"corpus_path={tmp_path / 'benchmarks/materialized/beir_scifact/quick/corpus.parquet'} "
        f"queries_path={tmp_path / 'benchmarks/materialized/beir_scifact/quick/queries.parquet'} "
        f"judgments_path={tmp_path / 'benchmarks/materialized/beir_scifact/quick/judgments.tsv'}\n"
    )
    assert not (tmp_path / "benchmarks/materialized/beir_scifact").exists()


def test_resolve_data_files_pins_revision_and_sorts_glob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glob_calls: list[str] = []

    class FakeHfFileSystem:
        def glob(self, pattern: str) -> list[str]:
            glob_calls.append(pattern)
            return [
                "datasets/example/corpus@abc123/data/b.jsonl",
                "datasets/example/corpus@abc123/data/a.jsonl",
            ]

    monkeypatch.setattr(benchmark_fetch, "HfFileSystem", FakeHfFileSystem)

    resolved = benchmark_fetch._resolve_data_files(
        [
            "datasets/example/corpus/data/*.jsonl",
            "hf://datasets/example/queries/data/dev.tsv",
        ],
        revision="abc123",
    )

    assert glob_calls == ["datasets/example/corpus@abc123/data/*.jsonl"]
    assert resolved == [
        "hf://datasets/example/corpus@abc123/data/a.jsonl",
        "hf://datasets/example/corpus@abc123/data/b.jsonl",
        "hf://datasets/example/queries@abc123/data/dev.tsv",
    ]


def test_resolve_data_files_rejects_revision_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match pinned revision"):
        benchmark_fetch._resolve_data_files(
            ["hf://datasets/example/corpus@old/data/dev.tsv"],
            revision="abc123",
        )


def test_materialize_dataset_rejects_unpinned_source_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_manifest(
        tmp_path,
        dataset_id="beir_scifact",
        corpus_revision="main",
    )

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("invalid manifest should fail before fetching datasets")

    monkeypatch.setattr(benchmark_fetch, "resolve_repo_asset_path", _resolver(tmp_path))
    monkeypatch.setattr(benchmark_fetch, "load_dataset", fail_if_called)

    with pytest.raises(ValueError, match="Expected pinned revision"):
        benchmark_fetch.materialize_dataset("beir_scifact", level=_quick_level())


def _write_manifest(
    tmp_path: Path,
    *,
    dataset_id: str,
    corpus_revision: str = "corpus-sha",
    queries_revision: str = "queries-sha",
    judgments_revision: str = "judgments-sha",
    trust_remote_code: bool = False,
) -> None:
    manifest_path = tmp_path / "benchmarks/contracts/datasets" / f"{dataset_id}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _ = manifest_path.write_text(
        "\n".join(
            (
                f"dataset_id: {dataset_id}",
                "name: Example SciFact",
                "language: en",
                "purpose_tags:",
                "  - passage-retrieval",
                f"corpus_path: benchmarks/materialized/{dataset_id}/corpus.parquet",
                f"queries_path: benchmarks/materialized/{dataset_id}/queries.parquet",
                f"judgments_path: benchmarks/materialized/{dataset_id}/judgments.tsv",
                "source:",
                "  corpus:",
                "    repo_id: example/scifact",
                "    config: corpus",
                "    split: corpus",
                f"    revision: {corpus_revision}",
                *( ["    trust_remote_code: true"] if trust_remote_code else [] ),
                "  queries:",
                "    repo_id: example/scifact",
                "    config: queries",
                "    split: queries",
                f"    revision: {queries_revision}",
                *( ["    trust_remote_code: true"] if trust_remote_code else [] ),
                "  judgments:",
                "    repo_id: example/scifact-qrels",
                "    config: default",
                "    split: test",
                f"    revision: {judgments_revision}",
                *( ["    trust_remote_code: true"] if trust_remote_code else [] ),
                "field_mappings:",
                "  corpus_id_keys:",
                "    - _id",
                "  corpus_text_keys:",
                "    - text",
                "    - title",
                "    - content",
                "  query_id_keys:",
                "    - _id",
                "  query_text_keys:",
                "    - text",
                "  judgment_query_id_keys:",
                "    - query-id",
                "  judgment_doc_id_keys:",
                "    - corpus-id",
                "  judgment_relevance_keys:",
                "    - score",
                "supported_levels:",
                "  - quick",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest_with_query_text_keys(
    tmp_path: Path,
    *,
    dataset_id: str,
    query_text_keys: tuple[str, ...],
) -> None:
    manifest_path = tmp_path / "benchmarks/contracts/datasets" / f"{dataset_id}.yaml"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    start = lines.index("  query_text_keys:")
    end = start + 1
    while end < len(lines) and lines[end].startswith("    - "):
        end += 1
    replacement = ["  query_text_keys:", *(f"    - {key}" for key in query_text_keys)]
    _ = manifest_path.write_text(
        "\n".join((*lines[:start], *replacement, *lines[end:])) + "\n",
        encoding="utf-8",
    )


def _quick_level() -> LevelConfig:
    return LevelConfig(level_id="quick", query_cap=10, corpus_cap=10)


def _resolver(root: Path) -> Callable[[str | Path], Path]:
    def resolve(relative_path: str | Path) -> Path:
        return root / Path(relative_path)

    return resolve


def _asset_resolver(
    root: Path,
) -> Callable[..., dict[str, Path]]:
    def resolve(
        manifest: DatasetManifest,
        *,
        level_id: str | None = None,
    ) -> dict[str, Path]:
        materialized_dir = root / "benchmarks/materialized" / manifest.dataset_id
        if level_id is not None:
            materialized_dir /= level_id
        return {
            "corpus": materialized_dir / "corpus.parquet",
            "queries": materialized_dir / "queries.parquet",
            "judgments": materialized_dir / "judgments.tsv",
        }

    return resolve
