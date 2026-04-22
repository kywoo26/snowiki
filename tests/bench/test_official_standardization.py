"""End-to-end tests for official benchmark standardization."""

from __future__ import annotations

from snowiki.bench.policy import (
    OFFICIAL_BALANCED_CORE,
    get_layer_policy,
    get_quick_pr_suite,
    get_scheduled_suite,
    is_local_diagnostic,
    is_official,
)


class TestOfficialBackbone:
    """Verify the exact official dataset backbone."""

    def test_exact_12_datasets(self) -> None:
        expected = {
            "ms_marco_passage",
            "trec_dl_2019_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "miracl_ja",
            "miracl_zh",
            "mr_tydi_ko",
            "beir_nq",
            "beir_scifact",
            "beir_fiqa_2018",
            "beir_arguana",
        }
        actual = {d.dataset_id for d in OFFICIAL_BALANCED_CORE}
        assert actual == expected

    def test_all_official_standard(self) -> None:
        for entry in OFFICIAL_BALANCED_CORE:
            assert entry.authority_class == "official_standard"
            assert is_official(entry.dataset_id)
            assert not is_local_diagnostic(entry.dataset_id)


class TestLayerContracts:
    """Verify layer-specific metric contracts."""

    def test_pr_quick_exact_metrics(self) -> None:
        policy = get_layer_policy("pr_official_quick")
        assert policy["metrics"] == ("nDCG@10", "P95 latency")
        assert policy["blocking"] is True

    def test_scheduled_exact_metrics(self) -> None:
        policy = get_layer_policy("scheduled_official_broad")
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
            "miracl_ko",
            "miracl_ja",
            "miracl_zh",
        )

    def test_scheduled_suite_exact(self) -> None:
        suite = get_scheduled_suite()
        assert len(suite) == 12
        assert set(suite) == {d.dataset_id for d in OFFICIAL_BALANCED_CORE}


class TestLocalDiagnosticIsolation:
    """Verify local diagnostics are excluded from official paths."""

    def test_regression_is_diagnostic(self) -> None:
        assert is_local_diagnostic("regression")
        assert not is_official("regression")

    def test_shaped_is_diagnostic(self) -> None:
        assert is_local_diagnostic("snowiki_shaped")
        assert not is_official("snowiki_shaped")

    def test_holdout_is_diagnostic(self) -> None:
        assert is_local_diagnostic("hidden_holdout")
        assert not is_official("hidden_holdout")

    def test_no_diagnostic_in_official_registry(self) -> None:
        for entry in OFFICIAL_BALANCED_CORE:
            assert not is_local_diagnostic(entry.dataset_id)
