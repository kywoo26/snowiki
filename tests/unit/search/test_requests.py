from __future__ import annotations

from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest

from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.requests import RuntimeSearchRequest
from snowiki.search.scoring import RuntimeScoringPolicy


def _call_with_legacy_keywords(call: Any) -> None:
    call("contract", limit=3)


class RecordingRuntimeSearchIndex:
    def __init__(self, hits: Sequence[SearchHit]) -> None:
        self._hits: list[SearchHit] = list(hits)
        self.requests: list[RuntimeSearchRequest] = []

    def search(self, request: RuntimeSearchRequest) -> Sequence[SearchHit]:
        self.requests.append(request)
        return self._hits[: request.candidate_limit]


def _hit(document_id: str) -> SearchHit:
    return SearchHit(
        document=SearchDocument(
            id=document_id,
            path=f"pages/{document_id}.md",
            kind="page",
            title=document_id,
            content=document_id,
        ),
        score=1.0,
        matched_terms=(document_id,),
    )


def test_runtime_search_request_has_expected_fields_and_defaults() -> None:
    request = RuntimeSearchRequest(query="snowiki", candidate_limit=1)

    assert request.query == "snowiki"
    assert request.candidate_limit == 1
    assert request.recorded_after is None
    assert request.recorded_before is None
    assert request.exact_path_bias is False
    assert request.kind_weights is None
    assert request.scoring_policy is None


def test_runtime_search_request_is_immutable_after_construction() -> None:
    request = RuntimeSearchRequest(query="snowiki", candidate_limit=1)

    with pytest.raises(FrozenInstanceError):
        request.__setattr__("query", "changed")


def test_runtime_search_request_accepts_zero_candidate_limit() -> None:
    request = RuntimeSearchRequest(query="snowiki", candidate_limit=0)

    assert request.candidate_limit == 0


def test_runtime_search_request_rejects_negative_candidate_limit() -> None:
    with pytest.raises(ValueError):
        RuntimeSearchRequest(query="snowiki", candidate_limit=-1)


def test_runtime_search_request_carries_filter_bias_weight_and_policy_fields() -> None:
    scoring_policy = RuntimeScoringPolicy()
    recorded_after = datetime(2026, 4, 1, tzinfo=UTC)
    recorded_before = datetime(2026, 4, 30, tzinfo=UTC)

    request = RuntimeSearchRequest(
        query="runtime contract",
        candidate_limit=3,
        recorded_after=recorded_after,
        recorded_before=recorded_before,
        exact_path_bias=True,
        kind_weights={"session": 1.15, "page": 0.85},
        scoring_policy=scoring_policy,
    )

    assert request.query == "runtime contract"
    assert request.candidate_limit == 3
    assert request.recorded_after == recorded_after
    assert request.recorded_before == recorded_before
    assert request.exact_path_bias is True
    assert request.kind_weights == {"session": 1.15, "page": 0.85}
    assert request.scoring_policy is scoring_policy


def test_runtime_search_index_accepts_request_and_returns_sequence_of_hits() -> None:
    index = RecordingRuntimeSearchIndex([_hit("first"), _hit("second")])
    request = RuntimeSearchRequest(query="contract", candidate_limit=1)

    hits = index.search(request)

    assert index.requests == [request]
    assert [hit.document.id for hit in hits] == ["first"]


def test_old_keyword_heavy_search_call_is_not_the_runtime_contract() -> None:
    index = RecordingRuntimeSearchIndex([_hit("first")])

    with pytest.raises(TypeError):
        _call_with_legacy_keywords(index.search)
