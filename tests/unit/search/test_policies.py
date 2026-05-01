from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from snowiki.search.queries.policies import (
    DATE_POLICY,
    KNOWN_ITEM_POLICY,
    TEMPORAL_POLICY,
    TOPICAL_POLICY,
    SearchIntentPolicy,
)


def test_search_intent_policy_construction_and_immutability() -> None:
    policy = SearchIntentPolicy(
        name="custom",
        candidate_multiplier=2,
        exact_path_bias=False,
        kind_weights={"page": 1.0},
        use_kind_blending=False,
    )

    assert policy.name == "custom"
    assert policy.candidate_multiplier == 2
    assert policy.exact_path_bias is False
    assert dict(policy.kind_weights) == {"page": 1.0}
    assert policy.use_kind_blending is False

    with pytest.raises(FrozenInstanceError):
        setattr(policy, "candidate_multiplier", 9)  # noqa: B010


def test_known_item_policy_uses_current_kiwi_path_and_kind_biases() -> None:
    assert KNOWN_ITEM_POLICY.name == "known-item"
    assert KNOWN_ITEM_POLICY.candidate_multiplier == 3
    assert KNOWN_ITEM_POLICY.exact_path_bias is True
    assert KNOWN_ITEM_POLICY.kind_weights == {"session": 1.15, "page": 0.85}
    assert KNOWN_ITEM_POLICY.use_kind_blending is False


def test_topical_policy_uses_current_kiwi_candidate_expansion_and_blending() -> None:
    assert TOPICAL_POLICY.name == "topical"
    assert TOPICAL_POLICY.candidate_multiplier == 4
    assert TOPICAL_POLICY.exact_path_bias is False
    assert TOPICAL_POLICY.kind_weights
    assert set(TOPICAL_POLICY.kind_weights) == {"session", "page"}
    assert all(weight == 1.0 for weight in TOPICAL_POLICY.kind_weights.values())
    assert TOPICAL_POLICY.use_kind_blending is True


def test_temporal_policy_uses_current_kiwi_candidate_expansion_without_path_bias() -> None:
    assert TEMPORAL_POLICY.name == "temporal"
    assert TEMPORAL_POLICY.candidate_multiplier == 3
    assert TEMPORAL_POLICY.exact_path_bias is False
    assert all(weight == 1.0 for weight in TEMPORAL_POLICY.kind_weights.values())
    assert TEMPORAL_POLICY.use_kind_blending is False


def test_date_policy_matches_temporal_values_with_distinct_identity() -> None:
    assert DATE_POLICY.name == "date"
    assert DATE_POLICY.candidate_multiplier == TEMPORAL_POLICY.candidate_multiplier
    assert DATE_POLICY.exact_path_bias == TEMPORAL_POLICY.exact_path_bias
    assert dict(DATE_POLICY.kind_weights) == dict(TEMPORAL_POLICY.kind_weights)
    assert DATE_POLICY.use_kind_blending == TEMPORAL_POLICY.use_kind_blending
    assert DATE_POLICY is not TEMPORAL_POLICY


@pytest.mark.parametrize("final_limit", [-5, -1, 0])
def test_candidate_limit_returns_zero_for_non_positive_final_limits(
    final_limit: int,
) -> None:
    assert KNOWN_ITEM_POLICY.candidate_limit(final_limit) == 0


def test_candidate_limit_uses_intent_multiplier_but_never_under_final_limit() -> None:
    custom_policy = SearchIntentPolicy(
        name="single-pass",
        candidate_multiplier=0,
        exact_path_bias=False,
        kind_weights={},
        use_kind_blending=False,
    )

    assert KNOWN_ITEM_POLICY.candidate_limit(2) == 6
    assert TOPICAL_POLICY.candidate_limit(3) == 12
    assert TEMPORAL_POLICY.candidate_limit(4) == 12
    assert custom_policy.candidate_limit(5) == 5


def test_policy_presets_are_immutable_named_constants() -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(KNOWN_ITEM_POLICY, "exact_path_bias", False)  # noqa: B010
    with pytest.raises(TypeError):
        cast(MutableMapping[str, float], KNOWN_ITEM_POLICY.kind_weights)["session"] = 1.0
