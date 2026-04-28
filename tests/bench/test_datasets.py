from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.bench.datasets import (
    load_dataset_manifest,
    load_matrix,
    resolve_dataset_assets,
)


def test_load_dataset_manifest_reads_source_aware_beir_contract() -> None:
    manifest = load_dataset_manifest("benchmarks/contracts/datasets/beir_scifact.yaml")

    assert manifest.dataset_id == "beir_scifact"
    assert manifest.name == "BEIR SciFact"
    assert manifest.language == "en"
    assert manifest.purpose_tags == ("passage-retrieval", "scientific-literature", "en")
    assert manifest.corpus_path == "benchmarks/materialized/beir_scifact/corpus.parquet"
    assert manifest.queries_path == "benchmarks/materialized/beir_scifact/queries.parquet"
    assert manifest.judgments_path == "benchmarks/materialized/beir_scifact/judgments.tsv"
    assert manifest.supported_levels == ("quick", "standard")
    assert manifest.field_mappings["corpus_id_keys"] == ("_id",)
    assert manifest.source["corpus"].repo_id == "BeIR/scifact"
    assert manifest.source["corpus"].config == "corpus"
    assert manifest.source["corpus"].split == "corpus"
    assert manifest.source["corpus"].revision == "b3b5335604bf5ee3c4447671af975ea25143d4f5"
    assert manifest.source["judgments"].repo_id == "BeIR/scifact-qrels"
    assert manifest.source["judgments"].config == "default"
    assert manifest.source["judgments"].split == "test"
    assert manifest.source["judgments"].revision == "2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029"


def test_load_dataset_manifest_reads_source_aware_miracl_contract() -> None:
    manifest = load_dataset_manifest("benchmarks/contracts/datasets/miracl_ko.yaml")

    assert manifest.dataset_id == "miracl_ko"
    assert manifest.name == "MIRACL Korean"
    assert manifest.language == "ko"
    assert manifest.corpus_path == "benchmarks/materialized/miracl_ko/corpus.parquet"
    assert manifest.queries_path == "benchmarks/materialized/miracl_ko/queries.parquet"
    assert manifest.judgments_path == "benchmarks/materialized/miracl_ko/judgments.tsv"
    assert manifest.source["corpus"].repo_id == "miracl/miracl-corpus"
    assert manifest.source["corpus"].config == "ko"
    assert manifest.source["corpus"].split == "train"
    assert manifest.source["corpus"].revision == "d921ec7e349ce0d28daf30b2da9da5ee698bef0d"
    assert manifest.source["queries"].repo_id == "miracl/miracl"
    assert manifest.source["queries"].config == "ko"
    assert manifest.source["queries"].split == "dev"
    assert manifest.source["queries"].revision == "5be20db9509754dadad47689368639fcec739c00"
    assert manifest.source["judgments"].split == "dev"


def test_load_matrix_reads_official_contract() -> None:
    matrix = load_matrix("benchmarks/contracts/official_matrix.yaml")

    assert matrix.matrix_id == "official_core"
    assert matrix.datasets == (
        "beir_nq",
        "beir_scifact",
        "trec_dl_2020_passage",
        "miracl_ko",
    )
    assert tuple(matrix.levels) == ("quick", "standard")
    assert matrix.levels["quick"].query_cap == 150
    assert matrix.levels["quick"].corpus_cap == 50000
    assert matrix.levels["standard"].corpus_cap == 200000


def test_load_matrix_reads_snowiki_regression_contract() -> None:
    matrix = load_matrix("benchmarks/contracts/snowiki_regression_matrix.yaml")

    assert matrix.matrix_id == "snowiki_regression"
    assert matrix.datasets == ("snowiki_retrieval_regression",)
    assert tuple(matrix.levels) == ("regression",)
    assert matrix.levels["regression"].query_cap == 23
    assert matrix.levels["regression"].corpus_cap is None


def test_load_dataset_manifest_reads_snowiki_regression_contract() -> None:
    manifest = load_dataset_manifest(
        "benchmarks/contracts/datasets/snowiki_retrieval_regression.yaml"
    )

    assert manifest.dataset_id == "snowiki_retrieval_regression"
    assert manifest.language == "mixed"
    assert manifest.purpose_tags == (
        "product-regression",
        "analyzer-promotion",
        "snowiki-owned",
    )
    assert manifest.corpus_path == "benchmarks/regression/snowiki_retrieval/corpus.json"
    assert manifest.queries_path == "benchmarks/regression/snowiki_retrieval/queries.json"
    assert manifest.judgments_path == "benchmarks/regression/snowiki_retrieval/judgments.json"
    assert manifest.supported_levels == ("regression",)


def test_snowiki_regression_assets_cover_gate_slices() -> None:
    manifest = load_dataset_manifest(
        "benchmarks/contracts/datasets/snowiki_retrieval_regression.yaml"
    )
    assets = resolve_dataset_assets(manifest, level_id="regression")

    assert set(assets) == {"corpus", "queries", "judgments"}
    assert all(path.is_file() for path in assets.values())


def test_resolve_dataset_assets_rejects_unsafe_level_id() -> None:
    manifest = load_dataset_manifest("benchmarks/contracts/datasets/beir_scifact.yaml")

    with pytest.raises(ValueError, match="Unsafe benchmark level ID"):
        resolve_dataset_assets(manifest, level_id="../escape")


def test_load_dataset_manifest_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError, match=str(missing_path)):
        load_dataset_manifest(missing_path)


def test_load_dataset_manifest_raises_for_malformed_yaml(tmp_path: Path) -> None:
    manifest_path = tmp_path / "invalid.yaml"
    manifest_path.write_text("- dataset_id: broken\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected YAML mapping"):
        load_dataset_manifest(manifest_path)


@pytest.mark.parametrize("revision", ["main", "master", "   "])
def test_load_dataset_manifest_rejects_branch_revision(
    tmp_path: Path,
    revision: str,
) -> None:
    manifest_path = tmp_path / "invalid_revision.yaml"
    manifest_path.write_text(
        "\n".join(
            (
                "dataset_id: broken",
                "name: Broken Dataset",
                "language: en",
                "purpose_tags:",
                "  - test",
                "corpus_path: benchmarks/materialized/broken/corpus.parquet",
                "queries_path: benchmarks/materialized/broken/queries.parquet",
                "judgments_path: benchmarks/materialized/broken/judgments.tsv",
                "source:",
                "  corpus:",
                "    repo_id: broken/corpus",
                "    config: corpus",
                "    split: corpus",
                f"    revision: {revision}",
                "  queries:",
                "    repo_id: broken/queries",
                "    config: queries",
                "    split: queries",
                "    revision: abc123",
                "  judgments:",
                "    repo_id: broken/judgments",
                "    config: default",
                "    split: test",
                "    revision: def456",
                "field_mappings:",
                "  corpus_id_keys:",
                "    - _id",
                "  corpus_text_keys:",
                "    - text",
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

    with pytest.raises(ValueError, match="Expected pinned revision"):
        load_dataset_manifest(manifest_path)
