"""Tests for the official benchmark policy contract."""

from __future__ import annotations

from snowiki.bench.policy import (
    OFFICIAL_BALANCED_CORE,
    get_dataset_authority,
    get_dataset_entry,
    get_layer_policy,
    get_official_datasets_by_language,
    get_quick_pr_suite,
    get_scheduled_suite,
    is_local_diagnostic,
    is_official,
    resolve_policy,
)


class TestOfficialRegistry:
    """Tests for the official balanced-core benchmark registry."""

    def test_registry_has_expected_datasets(self) -> None:
        expected_ids = {
            "ms_marco_passage",
            "trec_dl_2020_passage",
            "miracl_ko",
            "miracl_en",
            "beir_nq",
            "beir_scifact",
        }
        actual_ids = {d.dataset_id for d in OFFICIAL_BALANCED_CORE}
        assert actual_ids == expected_ids

    def test_all_entries_are_official_standard(self) -> None:
        for entry in OFFICIAL_BALANCED_CORE:
            assert entry.authority_class == "official_standard"

    def test_registry_has_6_datasets(self) -> None:
        assert len(OFFICIAL_BALANCED_CORE) == 6


class TestLanguageAxes:
    """Tests for language axis coverage."""

    def test_english_datasets(self) -> None:
        en_datasets = get_official_datasets_by_language("en")
        en_ids = {d.dataset_id for d in en_datasets}
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
        ko_ids = {d.dataset_id for d in ko_datasets}
        expected = {"miracl_ko"}
        assert ko_ids == expected

    def test_multilingual_datasets(self) -> None:
        multi_datasets = get_official_datasets_by_language("multilingual")
        assert multi_datasets == ()


class TestLocalDiagnostics:
    """Tests for local diagnostic dataset classification."""

    def test_regression_is_local_diagnostic(self) -> None:
        assert is_local_diagnostic("regression")
        assert not is_official("regression")
        assert get_dataset_authority("regression") == "local_diagnostic"

    def test_snowiki_shaped_is_local_diagnostic(self) -> None:
        assert is_local_diagnostic("snowiki_shaped")
        assert not is_official("snowiki_shaped")
        assert get_dataset_authority("snowiki_shaped") == "local_diagnostic"

    def test_hidden_holdout_is_local_diagnostic(self) -> None:
        assert is_local_diagnostic("hidden_holdout")
        assert not is_official("hidden_holdout")
        assert get_dataset_authority("hidden_holdout") == "local_diagnostic"


class TestOfficialDatasets:
    """Tests for official dataset classification."""

    def test_ms_marco_is_official(self) -> None:
        assert is_official("ms_marco_passage")
        assert not is_local_diagnostic("ms_marco_passage")
        assert get_dataset_authority("ms_marco_passage") == "official_standard"

    def test_miracl_ko_is_official(self) -> None:
        assert is_official("miracl_ko")
        assert get_dataset_authority("miracl_ko") == "official_standard"

    def test_unknown_dataset_is_candidate(self) -> None:
        assert get_dataset_authority("unknown_dataset") == "official_candidate"
        assert not is_official("unknown_dataset")
        assert not is_local_diagnostic("unknown_dataset")


class TestLayerPolicy:
    """Tests for execution layer configurations."""

    def test_pr_official_quick_defaults(self) -> None:
        policy = get_layer_policy("pr_official_quick")
        assert policy["sample_mode"] == "quick"
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is True

    def test_scheduled_official_broad_defaults(self) -> None:
        policy = get_layer_policy("scheduled_official_broad")
        assert policy["sample_mode"] == "standard"
        assert policy["metrics"] == ("nDCG@10", "Recall@100", "MRR@10", "P95 latency")
        assert policy["blocking"] is False

    def test_release_proof_defaults(self) -> None:
        policy = get_layer_policy("release_proof")
        assert policy["sample_mode"] == "full"
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
        # All must be official
        for dataset_id in suite:
            assert is_official(dataset_id)

    def test_scheduled_suite(self) -> None:
        suite = get_scheduled_suite()
        assert len(suite) == 6
        # All must be official
        for dataset_id in suite:
            assert is_official(dataset_id)


class TestPolicyResolution:
    """Tests for full policy resolution."""

    def test_resolve_pr_quick_ms_marco(self) -> None:
        policy = resolve_policy("pr_official_quick", "ms_marco_passage")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "official_standard"
        assert policy.language == "en"
        assert policy.dataset_id == "ms_marco_passage"

    def test_resolve_scheduled_miracl_ko(self) -> None:
        policy = resolve_policy("scheduled_official_broad", "miracl_ko")
        assert policy.layer == "scheduled_official_broad"
        assert policy.authority == "official_standard"
        assert policy.language == "ko"

    def test_resolve_pr_quick_regression(self) -> None:
        policy = resolve_policy("pr_official_quick", "regression")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "local_diagnostic"
        assert policy.language == "multilingual"

    def test_resolve_unknown_dataset(self) -> None:
        policy = resolve_policy("scheduled_official_broad", "unknown_xyz")
        assert policy.authority == "official_candidate"
        assert policy.language == "multilingual"


class TestDatasetEntryLookup:
    """Tests for dataset entry lookup."""

    def test_get_existing_dataset(self) -> None:
        entry = get_dataset_entry("ms_marco_passage")
        assert entry is not None
        assert entry.name == "MS MARCO Passage Ranking"
        assert entry.language_axis == "en"

    def test_get_nonexistent_dataset(self) -> None:
        assert get_dataset_entry("nonexistent") is None
