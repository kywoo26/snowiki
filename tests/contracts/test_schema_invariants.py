from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from snowiki.schema import (
    Artifact,
    CURRENT_SCHEMA_VERSION,
    Event,
    IngestStatus,
    Message,
    Part,
    Provenance,
    SchemaVersion,
    Session,
    migrate_payload,
    register_migration,
)

SchemaModel = type[BaseModel]

MODEL_REQUIRED_FIELDS = {
    Session: {
        "id",
        "source",
        "identity_keys",
        "started_at",
        "updated_at",
        "metadata",
        "status",
        "provenance",
    },
    Event: {
        "id",
        "session_id",
        "source",
        "identity_keys",
        "type",
        "timestamp",
        "content",
        "provenance",
    },
    Message: {
        "id",
        "session_id",
        "source",
        "identity_keys",
        "role",
        "created_at",
        "parts",
        "provenance",
    },
    Part: {
        "id",
        "message_id",
        "source",
        "identity_keys",
        "type",
        "index",
        "provenance",
    },
    Artifact: {
        "id",
        "session_id",
        "source",
        "identity_keys",
        "type",
        "created_at",
        "uri",
        "provenance",
    },
    Provenance: {
        "id",
        "source",
        "identity_keys",
        "raw_uri",
        "raw_id",
        "raw_kind",
        "captured_at",
    },
    IngestStatus: {
        "id",
        "source",
        "identity_keys",
        "record_type",
        "record_id",
        "state",
        "first_seen_at",
        "last_seen_at",
        "provenance",
    },
}


@pytest.mark.parametrize(
    ("model_cls", "required_fields"),
    MODEL_REQUIRED_FIELDS.items(),
)
def test_required_field_invariants(
    model_cls: SchemaModel,
    required_fields: set[str],
) -> None:
    actual_required = {
        name for name, field in model_cls.model_fields.items() if field.is_required()
    }
    assert required_fields <= actual_required


@pytest.mark.parametrize("model_cls", tuple(MODEL_REQUIRED_FIELDS))
def test_source_metadata_is_optional_namespace(
    model_cls: SchemaModel,
    valid_payloads: dict[SchemaModel, dict[str, Any]],
) -> None:
    payload = dict(valid_payloads[model_cls])
    payload.pop("source_metadata", None)
    instance = model_cls.model_validate(payload)
    assert getattr(instance, "source_metadata", None) is None


@pytest.mark.parametrize("model_cls", tuple(MODEL_REQUIRED_FIELDS))
def test_vendor_specific_fields_are_not_first_class(
    model_cls: SchemaModel,
) -> None:
    field_names = set(model_cls.model_fields)
    assert not any(
        name.startswith(("claude_", "anthropic_", "omo_", "opencode_"))
        for name in field_names
    )


@pytest.mark.parametrize("model_cls", tuple(MODEL_REQUIRED_FIELDS))
def test_no_mutable_defaults(model_cls: SchemaModel) -> None:
    for field in model_cls.model_fields.values():
        assert not isinstance(field.default, (dict, list, set))


def test_valid_instances_default_to_current_schema_version(
    valid_instances: dict[SchemaModel, BaseModel],
) -> None:
    assert all(
        getattr(instance, "schema_version") == CURRENT_SCHEMA_VERSION
        for instance in valid_instances.values()
    )


def test_part_requires_payload_reference(
    valid_part_payload: dict[str, Any],
) -> None:
    payload = dict(valid_part_payload)
    payload.pop("text", None)
    payload.pop("data", None)
    payload.pop("artifact_id", None)

    with pytest.raises(ValueError, match="part requires text, data, or artifact_id"):
        Part.model_validate(payload)


def test_migration_hooks_upgrade_payloads() -> None:
    register_migration(
        SchemaVersion.V1_LEGACY,
        SchemaVersion.V2_CANONICAL,
        lambda payload: {**payload, "migrated": True},
    )

    migrated = migrate_payload({"id": "legacy"}, SchemaVersion.V1_LEGACY)

    assert migrated["migrated"] is True
    assert migrated["schema_version"] == SchemaVersion.V2_CANONICAL
