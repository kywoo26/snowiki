from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from snowiki.schema import (
    Artifact,
    Event,
    IngestStatus,
    Message,
    Part,
    Provenance,
    Session,
)

SchemaModel = type[BaseModel]


def _assert_missing_field(exc: ValidationError, field_name: str) -> None:
    assert any(error["loc"] == (field_name,) for error in exc.errors())


@pytest.mark.parametrize(
    "model_cls", (Provenance, Part, Message, Artifact, Session, Event, IngestStatus)
)
def test_adapters_reject_missing_identity_keys(
    model_cls: SchemaModel,
    missing_identity_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model_cls.model_validate(missing_identity_payloads[model_cls])

    _assert_missing_field(exc_info.value, "identity_keys")


@pytest.mark.parametrize(
    "model_cls", (Provenance, Part, Message, Artifact, Session, Event, IngestStatus)
)
def test_adapters_reject_empty_identity_keys(
    model_cls: SchemaModel,
    empty_identity_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model_cls.model_validate(empty_identity_payloads[model_cls])

    assert any(error["loc"] == ("identity_keys",) for error in exc_info.value.errors())


@pytest.mark.parametrize(
    "model_cls", (Part, Message, Artifact, Session, Event, IngestStatus)
)
def test_adapters_reject_missing_provenance(
    model_cls: SchemaModel,
    missing_provenance_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model_cls.model_validate(missing_provenance_payloads[model_cls])

    _assert_missing_field(exc_info.value, "provenance")


def test_provenance_requires_raw_back_reference(
    valid_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    payload = dict(valid_payloads[Provenance])
    payload.pop("raw_uri", None)

    with pytest.raises(ValidationError) as exc_info:
        Provenance.model_validate(payload)

    _assert_missing_field(exc_info.value, "raw_uri")


def test_vendor_specific_fields_must_live_in_source_metadata(
    valid_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    payload = dict(valid_payloads[Session])
    payload["claude_session_path"] = "sessions/session-1.jsonl"

    with pytest.raises(ValidationError) as exc_info:
        Session.model_validate(payload)

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
