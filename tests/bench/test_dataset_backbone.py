"""Tests for the official benchmark dataset backbone."""

from __future__ import annotations

from typing import cast

from snowiki.bench.datasets import (
    BENCHMARK_DATASET_IDS,
    BENCHMARK_DATASET_REGISTRY,
)
from snowiki.bench.policy import OFFICIAL_BALANCED_CORE, is_official


class TestOfficialDatasetRegistry:
    """Tests that official datasets are registered in the fetch system."""

    def test_all_official_datasets_in_registry(self) -> None:
        official_ids = {d.dataset_id for d in OFFICIAL_BALANCED_CORE}
        registry_ids = set(BENCHMARK_DATASET_IDS)
        missing = official_ids - registry_ids
        assert not missing, f"Official datasets missing from registry: {missing}"

    def test_registry_has_expected_datasets(self) -> None:
        expected = {
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
            "beir_nfcorpus",
        }
        actual = set(BENCHMARK_DATASET_IDS)
        assert expected <= actual, f"Missing datasets: {expected - actual}"

    def test_official_datasets_have_specs(self) -> None:
        from snowiki.bench.datasets import BenchmarkDatasetId

        for entry in OFFICIAL_BALANCED_CORE:
            dataset_id = entry.dataset_id
            spec = BENCHMARK_DATASET_REGISTRY[cast(BenchmarkDatasetId, dataset_id)]
            assert spec.dataset_id == dataset_id
            assert spec.tier == "public_anchor"
            assert spec.sources

    def test_beir_datasets_have_separate_qrels(self) -> None:
        from snowiki.bench.datasets import BenchmarkDatasetId

        beir_datasets: list[BenchmarkDatasetId] = ["beir_nq", "beir_scifact"]
        for dataset_id in beir_datasets:
            spec = BENCHMARK_DATASET_REGISTRY[dataset_id]
            labels = {s.label for s in spec.sources}
            assert "corpus_queries" in labels
            assert "qrels" in labels

    def test_miracl_datasets_use_single_source(self) -> None:
        from snowiki.bench.datasets import BenchmarkDatasetId

        miracl_datasets: list[BenchmarkDatasetId] = ["miracl_ko", "miracl_en"]
        for dataset_id in miracl_datasets:
            spec = BENCHMARK_DATASET_REGISTRY[dataset_id]
            assert len(spec.sources) == 1
            assert spec.sources[0].label == "dataset"


class TestDatasetAuthority:
    """Tests for dataset authority classification."""

    def test_official_datasets_are_official(self) -> None:
        for dataset_id in (d.dataset_id for d in OFFICIAL_BALANCED_CORE):
            assert is_official(dataset_id), f"{dataset_id} should be official"

    def test_local_diagnostics_not_official(self) -> None:
        from snowiki.bench.policy import is_local_diagnostic

        assert is_local_diagnostic("regression")
        assert is_local_diagnostic("snowiki_shaped")
        assert is_local_diagnostic("hidden_holdout")
        assert not is_official("regression")
        assert not is_official("snowiki_shaped")
        assert not is_official("hidden_holdout")
