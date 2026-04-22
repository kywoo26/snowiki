"""Tests for benchmark execution boundary and namespace separation."""

from __future__ import annotations

import pytest

from snowiki.bench.policy import (
    get_dataset_authority,
    is_official,
    is_regression_harness,
    resolve_policy,
)


class TestNamespaceBoundary:
    """Tests for official vs regression namespace separation."""

    def test_official_dataset_authority(self) -> None:
        assert get_dataset_authority("ms_marco_passage") == "official_suite"
        assert get_dataset_authority("miracl_ko") == "official_suite"
        assert get_dataset_authority("beir_scifact") == "official_suite"

    def test_regression_harness_authority(self) -> None:
        assert get_dataset_authority("regression") == "regression_harness"

    def test_unknown_dataset_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="unsupported benchmark dataset"):
            _ = get_dataset_authority("unknown_xyz")

    def test_regression_harness_not_official(self) -> None:
        assert is_regression_harness("regression")
        assert not is_official("regression")


class TestPolicyResolution:
    """Tests for full policy resolution with layer and dataset."""

    def test_resolve_official_pr_quick(self) -> None:
        policy = resolve_policy("pr_official_quick", "ms_marco_passage")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "official_suite"
        assert policy.language == "en"
        assert policy.dataset_id == "ms_marco_passage"

    def test_resolve_official_scheduled(self) -> None:
        policy = resolve_policy("scheduled_official_standard", "miracl_ko")
        assert policy.layer == "scheduled_official_standard"
        assert policy.authority == "official_suite"
        assert policy.language == "ko"

    def test_resolve_regression_harness(self) -> None:
        policy = resolve_policy("pr_official_quick", "regression")
        assert policy.layer == "pr_official_quick"
        assert policy.authority == "regression_harness"

    def test_release_proof_disabled_by_default(self) -> None:
        from snowiki.bench.policy import get_layer_policy

        policy = get_layer_policy("release_proof")
        assert policy["enabled_by_default"] is False
