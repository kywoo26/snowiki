"""End-to-end tests for official benchmark standardization."""

from __future__ import annotations

from snowiki.bench.contract.policy import (
    get_layer_policy,
    get_quick_pr_suite,
    get_scheduled_suite,
    is_official,
    is_regression_harness,
)
from snowiki.bench.runtime.catalog import OFFICIAL_BENCHMARK_SUITE


class TestOfficialBackbone:
    """Verify the exact official dataset backbone."""

    def test_exact_6_datasets(self) -> None:
        expected = {
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        }
        actual = {d.dataset_id for d in OFFICIAL_BENCHMARK_SUITE}
        assert actual == expected

    def test_all_official_suite(self) -> None:
        for entry in OFFICIAL_BENCHMARK_SUITE:
            assert entry.authority_class == "official_suite"
            assert is_official(entry.dataset_id)
            assert not is_regression_harness(entry.dataset_id)


class TestLayerContracts:
    """Verify layer-specific metric contracts."""

    def test_pr_quick_exact_metrics(self) -> None:
        policy = get_layer_policy("pr_official_quick")
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True

    def test_scheduled_exact_metrics(self) -> None:
        policy = get_layer_policy("scheduled_official_standard")
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is False

    def test_release_proof_disabled(self) -> None:
        policy = get_layer_policy("release_proof")
        assert policy["enabled_by_default"] is False


class TestSuiteDefinitions:
    """Verify deterministic suite definitions."""

    def test_quick_suite_exact(self) -> None:
        suite = get_quick_pr_suite()
        assert suite == (
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        )

    def test_scheduled_suite_exact(self) -> None:
        suite = get_scheduled_suite()
        assert len(suite) == 6
        assert set(suite) == {d.dataset_id for d in OFFICIAL_BENCHMARK_SUITE}


class TestRegressionHarnessIsolation:
    """Verify the regression harness is excluded from official paths."""

    def test_regression_is_regression_harness(self) -> None:
        assert is_regression_harness("regression")
        assert not is_official("regression")

    def test_no_regression_harness_dataset_in_official_registry(self) -> None:
        for entry in OFFICIAL_BENCHMARK_SUITE:
            assert not is_regression_harness(entry.dataset_id)
