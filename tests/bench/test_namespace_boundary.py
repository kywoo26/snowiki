"""Tests for benchmark execution boundary and namespace separation."""

from __future__ import annotations

from snowiki.bench.policy import (
    get_dataset_authority,
    is_local_diagnostic,
    is_official,
    resolve_policy,
)


class TestNamespaceBoundary:
    """Tests for official vs diagnostic namespace separation."""

    def test_official_dataset_authority(self) -> None:
        assert get_dataset_authority("ms_marco_passage") == "official_standard"
        assert get_dataset_authority("miracl_ko") == "official_standard"
        assert get_dataset_authority("beir_scifact") == "official_standard"

    def test_local_diagnostic_authority(self) -> None:
        assert get_dataset_authority("regression") == "local_diagnostic"
        assert get_dataset_authority("snowiki_shaped") == "local_diagnostic"
        assert get_dataset_authority("hidden_holdout") == "local_diagnostic"

    def test_unknown_dataset_is_candidate(self) -> None:
        assert get_dataset_authority("unknown_xyz") == "official_candidate"

    def test_local_diagnostic_not_official(self) -> None:
        assert is_local_diagnostic("regression")
        assert is_local_diagnostic("snowiki_shaped")
        assert is_local_diagnostic("hidden_holdout")
        assert not is_official("regression")
        assert not is_official("snowiki_shaped")
        assert not is_official("hidden_holdout")


class TestPolicyResolution:
    """Tests for full policy resolution with layer and dataset."""

    def test_resolve_official_pr_quick(self) -> None:
        policy = resolve_policy("pr_official_quick", "ms_marco_passage")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "official_standard"
        assert policy.language == "en"
        assert policy.dataset_id == "ms_marco_passage"

    def test_resolve_official_scheduled(self) -> None:
        policy = resolve_policy("scheduled_official_broad", "miracl_ko")
        assert policy.layer == "scheduled_official_broad"
        assert policy.authority == "official_standard"
        assert policy.language == "ko"

    def test_resolve_local_diagnostic(self) -> None:
        policy = resolve_policy("pr_official_quick", "regression")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "local_diagnostic"

    def test_release_proof_disabled_by_default(self) -> None:
        from snowiki.bench.policy import get_layer_policy

        policy = get_layer_policy("release_proof")
        assert policy["enabled_by_default"] is False
