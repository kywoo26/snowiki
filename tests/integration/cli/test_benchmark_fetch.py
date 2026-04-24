from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner, Result

from snowiki.cli.main import app

pytestmark = pytest.mark.integration


def _write_benchmark_fixture_repo(repo_root: Path, *, dataset_id: str) -> None:
    contracts_dir = repo_root / "benchmarks" / "contracts"
    manifests_dir = contracts_dir / "datasets"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    _ = (contracts_dir / "official_matrix.yaml").write_text(
        dedent(
            f"""\
            matrix_id: official_core
            datasets:
              - {dataset_id}
            levels:
              quick:
                query_cap: 150
            """
        ),
        encoding="utf-8",
    )
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
        trust_remote_code: bool = False,
        streaming: bool = False,
    ) -> list[dict[str, object]]:
        del repo_id, config, revision, cache_dir, trust_remote_code, streaming
        return rows_by_split[split]

    monkeypatch.setattr("snowiki.benchmark_fetch.load_dataset", _fake_load_dataset)


def _invoke_benchmark_fetch(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(app, ["benchmark-fetch", *args])


def test_benchmark_fetch_help_shows_option_surface() -> None:
    result = _invoke_benchmark_fetch("--help")

    assert result.exit_code == 0
    for option in (
        "--matrix FILE",
        "--dataset TEXT",
        "--level TEXT",
        "--force / --no-force",
        "--dry-run / --no-dry-run",
    ):
        assert option in result.output


def test_benchmark_fetch_invalid_dataset_exits_two() -> None:
    result = _invoke_benchmark_fetch("--dataset", "missing_dataset")

    assert result.exit_code == 2
    assert "Unknown dataset selection: missing_dataset" in result.output


@pytest.mark.parametrize(
    ("matrix_arg", "expected_message"),
    [
        ("benchmarks/contracts/missing_matrix.yaml", "does not exist"),
        (".", "is a directory"),
    ],
)
def test_benchmark_fetch_invalid_matrix_exits_two_without_traceback(
    matrix_arg: str,
    expected_message: str,
) -> None:
    result = _invoke_benchmark_fetch("--matrix", matrix_arg)

    assert result.exit_code == 2
    assert expected_message in result.output
    assert "Traceback" not in result.output


def test_benchmark_fetch_materializes_temp_dataset_without_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    dataset_id = "tiny_fetch"
    _write_benchmark_fixture_repo(repo_root, dataset_id=dataset_id)
    _patch_temp_benchmark_repo(monkeypatch, repo_root)
    _patch_fake_benchmark_fetch_loader(monkeypatch)

    result = _invoke_benchmark_fetch("--dataset", dataset_id)

    assert result.exit_code == 0
    assert (
        f"dataset={dataset_id} level=quick action=materialized reason=missing_sidecar "
        "corpus=2 queries=2 judgments=2"
    ) in result.output
    materialized_root = repo_root / "benchmarks" / "materialized" / dataset_id / "quick"
    assert (materialized_root / "corpus.parquet").is_file()
    assert (materialized_root / "queries.parquet").is_file()
    assert (materialized_root / "judgments.tsv").is_file()
    assert (materialized_root / "materialization.json").is_file()


def test_benchmark_fetch_matrix_controls_default_dataset_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "benchmark-repo"
    dataset_id = "tiny_fetch"
    _write_benchmark_fixture_repo(repo_root, dataset_id=dataset_id)
    custom_matrix = repo_root / "benchmarks" / "contracts" / "custom_matrix.yaml"
    _ = custom_matrix.write_text(
        dedent(
            f"""\
            matrix_id: custom_one
            datasets:
              - {dataset_id}
            levels:
              quick:
                query_cap: 150
            """
        ),
        encoding="utf-8",
    )
    _patch_temp_benchmark_repo(monkeypatch, repo_root)
    _patch_fake_benchmark_fetch_loader(monkeypatch)

    result = _invoke_benchmark_fetch("--matrix", "benchmarks/contracts/custom_matrix.yaml")

    assert result.exit_code == 0
    assert f"dataset={dataset_id} level=quick action=materialized reason=missing_sidecar" in result.output
