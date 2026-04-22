"""Tests for the official benchmark dataset backbone."""

from __future__ import annotations

from typing import cast

from snowiki.bench.catalog import OFFICIAL_BENCHMARK_SUITE
from snowiki.bench.datasets import BENCHMARK_DATASET_IDS, BENCHMARK_DATASET_REGISTRY
from snowiki.bench.policy import is_official, is_regression_harness


class TestOfficialDatasetRegistry:
    """Tests that official datasets are registered in the fetch system."""

    def test_all_official_datasets_in_registry(self) -> None:
        official_ids = {d.dataset_id for d in OFFICIAL_BENCHMARK_SUITE}
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
        }
        actual = set(BENCHMARK_DATASET_IDS)
        assert actual == expected

    def test_official_datasets_have_specs(self) -> None:
        from snowiki.bench.datasets import BenchmarkDatasetId

        for entry in OFFICIAL_BENCHMARK_SUITE:
            dataset_id = entry.dataset_id
            spec = BENCHMARK_DATASET_REGISTRY[cast(BenchmarkDatasetId, dataset_id)]
            assert spec.dataset_id == dataset_id
            assert spec.tier == "official_suite"
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
        for dataset_id in (d.dataset_id for d in OFFICIAL_BENCHMARK_SUITE):
            assert is_official(dataset_id), f"{dataset_id} should be official"

    def test_regression_harness_not_official(self) -> None:
        assert is_regression_harness("regression")
        assert not is_official("regression")
