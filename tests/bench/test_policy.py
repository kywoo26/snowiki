"""Tests for the lean benchmark policy contract."""

from __future__ import annotations

import pytest

from snowiki.bench.catalog import (
    OFFICIAL_BALANCED_CORE,
    get_dataset_entry,
    get_official_datasets_by_language,
    is_official,
)
from snowiki.bench.policy import (
    get_dataset_authority,
    get_layer_policy,
    get_quick_pr_suite,
    get_scheduled_suite,
    is_local_diagnostic,
    is_regression_harness,
    resolve_policy,
)

pytestmark = pytest.mark.bench


class TestOfficialRegistry:
    """Tests for the official six-dataset benchmark registry."""

    def test_registry_has_expected_datasets(self) -> None:
        expected_ids = {
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        }
        actual_ids = {entry.dataset_id for entry in OFFICIAL_BALANCED_CORE}
        assert actual_ids == expected_ids

    def test_all_entries_are_official_suite(self) -> None:
        for entry in OFFICIAL_BALANCED_CORE:
            assert entry.authority_class == "official_suite"

    def test_registry_has_6_datasets(self) -> None:
        assert len(OFFICIAL_BALANCED_CORE) == 6


class TestLanguageAxes:
    """Tests for language axis coverage."""

    def test_english_datasets(self) -> None:
        en_datasets = get_official_datasets_by_language("en")
        en_ids = {entry.dataset_id for entry in en_datasets}
        expected = {
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        }
        assert en_ids == expected

    def test_korean_datasets(self) -> None:
        ko_datasets = get_official_datasets_by_language("ko")
        ko_ids = {entry.dataset_id for entry in ko_datasets}
        assert ko_ids == {"miracl_ko"}

    def test_multilingual_datasets(self) -> None:
        assert get_official_datasets_by_language("multilingual") == ()


class TestRegressionHarness:
    """Tests for the internal regression harness downgrade."""

    def test_regression_is_only_supported_non_official_runtime_dataset(self) -> None:
        assert is_regression_harness("regression")
        assert is_local_diagnostic("regression")
        assert not is_official("regression")
        assert get_dataset_authority("regression") == "regression_harness"

    @pytest.mark.parametrize(
        "dataset_id",
        ("unsupported_dataset", "legacy_dataset", "diagnostic_dataset", "review_queue"),
    )
    def test_removed_or_unknown_datasets_are_not_runtime_authorities(
        self, dataset_id: str
    ) -> None:
        assert not is_local_diagnostic(dataset_id)
        assert not is_official(dataset_id)
        with pytest.raises(ValueError, match="unsupported benchmark dataset"):
            _ = get_dataset_authority(dataset_id)


class TestOfficialDatasets:
    """Tests for official dataset classification."""

    def test_ms_marco_is_official(self) -> None:
        assert is_official("ms_marco_passage")
        assert not is_local_diagnostic("ms_marco_passage")
        assert get_dataset_authority("ms_marco_passage") == "official_suite"

    def test_miracl_ko_is_official(self) -> None:
        assert is_official("miracl_ko")
        assert get_dataset_authority("miracl_ko") == "official_suite"

    def test_unsupported_dataset_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported benchmark dataset"):
            _ = get_dataset_authority("unknown_dataset")


class TestLayerPolicy:
    """Tests for execution layer configurations."""

    def test_pr_official_quick_defaults(self) -> None:
        policy = get_layer_policy("pr_official_quick")
        assert policy["sample_mode"] == "quick"
        assert policy["sample_size"] == 150
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True

    def test_scheduled_official_standard_defaults(self) -> None:
        policy = get_layer_policy("scheduled_official_standard")
        assert policy["sample_mode"] == "standard"
        assert policy["sample_size"] == 500
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is False

    def test_release_proof_defaults(self) -> None:
        policy = get_layer_policy("release_proof")
        assert policy["sample_mode"] == "full"
        assert "sample_size" not in policy
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True
        assert policy["enabled_by_default"] is False


class TestSuiteDefinitions:
    """Tests for official suite definitions."""

    def test_quick_pr_suite(self) -> None:
        suite = get_quick_pr_suite()
        expected = (
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        )
        assert suite == expected
        for dataset_id in suite:
            assert is_official(dataset_id)

    def test_scheduled_suite(self) -> None:
        suite = get_scheduled_suite()
        assert len(suite) == 6
        for dataset_id in suite:
            assert is_official(dataset_id)


class TestPolicyResolution:
    """Tests for full policy resolution."""

    def test_resolve_pr_quick_ms_marco(self) -> None:
        policy = resolve_policy("pr_official_quick", "ms_marco_passage")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "official_suite"
        assert policy.language == "en"
        assert policy.dataset_id == "ms_marco_passage"

    def test_resolve_scheduled_miracl_ko(self) -> None:
        policy = resolve_policy("scheduled_official_standard", "miracl_ko")
        assert policy.layer == "scheduled_official_standard"
        assert policy.authority == "official_suite"
        assert policy.language == "ko"

    def test_resolve_legacy_scheduled_alias_normalizes_to_standard(self) -> None:
        policy = resolve_policy("scheduled_official_broad", "miracl_ko")
        assert policy.layer == "scheduled_official_standard"

    def test_resolve_pr_quick_regression(self) -> None:
        policy = resolve_policy("pr_official_quick", "regression")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "regression_harness"
        assert policy.language == "multilingual"

    def test_resolve_unknown_dataset_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported benchmark dataset"):
            _ = resolve_policy("scheduled_official_standard", "unknown_xyz")


class TestDatasetEntryLookup:
    """Tests for dataset entry lookup."""

    def test_get_existing_dataset(self) -> None:
        entry = get_dataset_entry("ms_marco_passage")
        assert entry is not None
        assert entry.name == "MS MARCO Passage Ranking"
        assert entry.language_axis == "en"

    def test_get_nonexistent_dataset(self) -> None:
        assert get_dataset_entry("nonexistent") is None
