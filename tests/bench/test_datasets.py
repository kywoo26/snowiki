from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.bench.datasets import load_dataset_manifest, load_matrix


def test_load_dataset_manifest_reads_valid_contract() -> None:
    manifest = load_dataset_manifest("benchmarks/contracts/datasets/ms_marco_passage.yaml")

    assert manifest.dataset_id == "ms_marco_passage"
    assert manifest.name == "MS MARCO Passage Ranking"
    assert manifest.language == "en"
    assert manifest.purpose_tags == ("passage-retrieval", "web-search", "en")
    assert manifest.supported_levels == ("quick", "standard", "full")
    assert manifest.field_mappings["corpus_id_keys"] == ("docid", "_id")


def test_load_matrix_reads_official_contract() -> None:
    matrix = load_matrix("benchmarks/contracts/official_matrix.yaml")

    assert matrix.matrix_id == "official_six"
    assert matrix.datasets == (
        "ms_marco_passage",
        "trec_dl_2020_passage",
        "miracl_ko",
        "miracl_en",
        "beir_nq",
        "beir_scifact",
    )
    assert tuple(matrix.levels) == ("quick", "standard", "full")
    assert matrix.levels["quick"].query_cap == 150
    assert matrix.levels["full"].note == "Full means min(all, 1000)."


def test_load_dataset_manifest_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError, match=str(missing_path)):
        load_dataset_manifest(missing_path)


def test_load_dataset_manifest_raises_for_malformed_yaml(tmp_path: Path) -> None:
    manifest_path = tmp_path / "invalid.yaml"
    manifest_path.write_text("- dataset_id: broken\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected YAML mapping"):
        load_dataset_manifest(manifest_path)
