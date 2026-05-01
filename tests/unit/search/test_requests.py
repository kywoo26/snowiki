from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any, get_type_hints

import pytest

from snowiki.search.models import SearchDocument, SearchHit
from snowiki.search.protocols import RuntimeSearchIndex
from snowiki.search.requests import RuntimeSearchRequest
from snowiki.search.scoring import RuntimeScoringPolicy

EXPECTED_REQUEST_FIELDS = (
    "query",
    "candidate_limit",
    "recorded_after",
    "recorded_before",
    "exact_path_bias",
    "kind_weights",
    "scoring_policy",
)


def _class_attribute(target: object, name: str) -> Any:
    return getattr(target, name)


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


def test_runtime_search_request_is_frozen_slotted_dataclass_with_expected_fields() -> None:
    assert is_dataclass(RuntimeSearchRequest)
    assert _class_attribute(RuntimeSearchRequest, "__dataclass_params__").frozen is True
    assert tuple(_class_attribute(RuntimeSearchRequest, "__slots__")) == EXPECTED_REQUEST_FIELDS

    request_fields = fields(RuntimeSearchRequest)
    assert tuple(field.name for field in request_fields) == EXPECTED_REQUEST_FIELDS

    hints = get_type_hints(RuntimeSearchRequest)
    assert hints == {
        "query": str,
        "candidate_limit": int,
        "recorded_after": datetime | None,
        "recorded_before": datetime | None,
        "exact_path_bias": bool,
        "kind_weights": Mapping[str, float] | None,
        "scoring_policy": RuntimeScoringPolicy | None,
    }

    defaults_by_name = {field.name: field.default for field in request_fields}
    assert defaults_by_name["recorded_after"] is None
    assert defaults_by_name["recorded_before"] is None
    assert defaults_by_name["exact_path_bias"] is False
    assert defaults_by_name["kind_weights"] is None
    assert defaults_by_name["scoring_policy"] is None
    assert "limit" not in defaults_by_name
    assert "final_limit" not in defaults_by_name


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


def test_runtime_search_index_protocol_accepts_request_and_returns_sequence_of_hits() -> None:
    signature = inspect.signature(RuntimeSearchIndex.search)
    parameters = list(signature.parameters.values())

    assert [(parameter.name, parameter.kind) for parameter in parameters] == [
        ("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ("request", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]

    hints = get_type_hints(RuntimeSearchIndex.search)
    assert hints["request"] is RuntimeSearchRequest
    assert hints["return"] == Sequence[SearchHit]

    index = RecordingRuntimeSearchIndex([_hit("first"), _hit("second")])
    request = RuntimeSearchRequest(query="contract", candidate_limit=1)

    hits = index.search(request)

    assert index.requests == [request]
    assert [hit.document.id for hit in hits] == ["first"]


def test_old_keyword_heavy_search_call_is_not_the_runtime_contract() -> None:
    parameters = inspect.signature(RuntimeSearchIndex.search).parameters
    assert "query" not in parameters
    assert "limit" not in parameters
    assert "candidate_limit" not in parameters

    index = RecordingRuntimeSearchIndex([_hit("first")])

    with pytest.raises(TypeError):
        _call_with_legacy_keywords(index.search)
