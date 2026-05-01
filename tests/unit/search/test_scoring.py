from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.scoring import RuntimeScoringPolicy

_DATACLASS_PARAMS = "__dataclass_params__"


def _is_frozen_dataclass(class_: object) -> bool:
    params = cast(Any, getattr(class_, _DATACLASS_PARAMS))
    return bool(params.frozen)


def _class_attribute(target: object, name: str) -> Any:
    return getattr(target, name)


def _set_frozen_field(instance: object, name: str, value: object) -> None:
    setattr(instance, name, value)


def _runtime_scoring_policy() -> Any:
    return cast(Any, RuntimeScoringPolicy)()


def _document(
    document_id: str,
    *,
    path: str | None = None,
    kind: str = "page",
    recorded_at: datetime | None = None,
) -> SearchDocument:
    return SearchDocument(
        id=document_id,
        path=path or f"docs/{document_id}.md",
        kind=kind,
        title=document_id,
        content="contract test fixture",
        recorded_at=recorded_at,
    )


def test_runtime_scoring_policy_is_frozen_slotted_dataclass_independent_of_indexes() -> None:
    assert is_dataclass(RuntimeScoringPolicy)
    assert _is_frozen_dataclass(RuntimeScoringPolicy) is True
    assert _class_attribute(RuntimeScoringPolicy, "__dataclass_params__").slots is True
    assert tuple(_class_attribute(RuntimeScoringPolicy, "__slots__")) == (
        "exact_path_token_boost",
        "path_phrase_boost",
        "recency_divisor",
        "default_kind_weight",
    )
    assert [field.name for field in fields(RuntimeScoringPolicy)] == [
        "exact_path_token_boost",
        "path_phrase_boost",
        "recency_divisor",
        "default_kind_weight",
    ]

    policy = _runtime_scoring_policy()
    assert policy.exact_path_token_boost == 2.0
    assert policy.path_phrase_boost == 2.5
    assert policy.recency_divisor == 10_000_000_000.0
    assert policy.default_kind_weight == 1.0

    with pytest.raises(FrozenInstanceError):
        _set_frozen_field(policy, "path_phrase_boost", 9.0)

    assert RuntimeScoringPolicy.__module__ == "snowiki.search.scoring"


def test_score_candidate_derives_sorted_matched_terms_from_token_evidence() -> None:
    hit = _runtime_scoring_policy().score_candidate(
        document=_document("runtime-policy"),
        raw_score=1.25,
        query_terms={"runtime", "policy", "missing"},
        document_terms={"policy", "runtime", "snowiki"},
        normalized_query="runtime policy",
        normalized_path="docs/runtime-policy.md",
    )

    assert hit == SearchHit(
        document=_document("runtime-policy"),
        score=1.25,
        matched_terms=("policy", "runtime"),
    )


def test_score_candidate_rejects_zero_score_candidates_without_match_evidence() -> None:
    hit = _runtime_scoring_policy().score_candidate(
        document=_document("unmatched"),
        raw_score=0.0,
        query_terms={"runtime"},
        document_terms={"snowiki"},
        normalized_query="runtime",
        normalized_path="docs/unmatched.md",
    )

    assert hit is None


def test_score_candidate_applies_path_boosts_kind_weight_and_recency_tie_break() -> None:
    recorded_at = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
    document = _document(
        "session-runtime-policy",
        path="sessions/runtime policy.md",
        kind="session",
        recorded_at=recorded_at,
    )

    hit = _runtime_scoring_policy().score_candidate(
        document=document,
        raw_score=1.0,
        query_terms={"runtime", "policy"},
        document_terms={"runtime"},
        normalized_query="runtime policy",
        normalized_path="sessions/runtime policy.md",
        exact_path_bias=True,
        kind_weights={"session": 1.15, "page": 0.85},
    )

    assert hit is not None
    expected_without_recency = (1.0 + 2.0 + 2.5) * 1.15
    expected = expected_without_recency + recorded_at.timestamp() / 10_000_000_000.0
    assert hit.score == pytest.approx(expected)
    assert hit.matched_terms == ("runtime",)


def test_score_candidate_uses_default_kind_weight_when_kind_is_not_named() -> None:
    hit = _runtime_scoring_policy().score_candidate(
        document=_document("kiwi-note", kind="note"),
        raw_score=2.0,
        query_terms={"kiwi"},
        document_terms={"kiwi"},
        normalized_query="kiwi intent",
        normalized_path="notes/other-note.md",
        kind_weights={"session": 1.15, "page": 0.85},
    )

    assert hit is not None
    assert hit.score == pytest.approx(2.0)


def test_score_candidate_keeps_path_phrase_boost_independent_from_exact_path_bias() -> None:
    hit = _runtime_scoring_policy().score_candidate(
        document=_document("runtime-policy", path="docs/runtime policy.md"),
        raw_score=0.0,
        query_terms={"unmatched"},
        document_terms=set(),
        normalized_query="runtime policy",
        normalized_path="docs/runtime policy.md",
        exact_path_bias=False,
    )

    assert hit is not None
    assert hit.score == pytest.approx(2.5)
    assert hit.matched_terms == ()


def test_sort_key_is_deterministic_for_score_path_and_document_id_ties() -> None:
    policy = _runtime_scoring_policy()
    hits = [
        SearchHit(document=_document("b", path="docs/shared.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("a", path="docs/shared.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("z", path="docs/alpha.md"), score=3.0, matched_terms=("x",)),
        SearchHit(document=_document("top", path="docs/top.md"), score=4.0, matched_terms=("x",)),
    ]

    ranked = sorted(hits, key=policy.sort_key)

    assert [hit.document.id for hit in ranked] == ["top", "z", "a", "b"]
