from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel

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


@pytest.fixture
def base_timestamp() -> datetime:
    return datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def valid_provenance_payload(base_timestamp: datetime) -> dict[str, object]:
    return {
        "id": "prov-session-1",
        "source": "claude",
        "identity_keys": ("raw:claude:session-1",),
        "raw_uri": "raw://claude/sessions/session-1.jsonl",
        "raw_id": "session-1",
        "raw_kind": "jsonl_session",
        "captured_at": base_timestamp,
        "locator": {"path": "sessions/session-1.jsonl", "line": 1},
        "checksum_sha256": "abc123",
        "source_metadata": {"adapter": "claude"},
    }


@pytest.fixture
def valid_part_payload(
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "part-1",
        "message_id": "message-1",
        "source": "claude",
        "identity_keys": ("part:claude:session-1:message-1:0",),
        "type": "text",
        "index": 0,
        "text": "Canonical schemas unlock adapter parity.",
        "provenance": copy.deepcopy(valid_provenance_payload),
        "source_metadata": {"block_type": "text"},
    }


@pytest.fixture
def valid_message_payload(
    base_timestamp: datetime,
    valid_part_payload: dict[str, object],
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "message-1",
        "session_id": "session-1",
        "source": "claude",
        "identity_keys": ("message:claude:session-1:message-1",),
        "role": "assistant",
        "created_at": base_timestamp,
        "parts": (copy.deepcopy(valid_part_payload),),
        "provenance": copy.deepcopy(valid_provenance_payload),
        "source_metadata": {"turn": 3},
    }


@pytest.fixture
def valid_artifact_payload(
    base_timestamp: datetime,
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "artifact-1",
        "session_id": "session-1",
        "source": "claude",
        "identity_keys": ("artifact:claude:session-1:artifact-1",),
        "type": "command_output",
        "created_at": base_timestamp,
        "uri": "artifact://session-1/output.txt",
        "mime_type": "text/plain",
        "size_bytes": 128,
        "checksum_sha256": "def456",
        "provenance": copy.deepcopy(valid_provenance_payload),
        "source_metadata": {"tool_name": "pytest"},
    }


@pytest.fixture
def valid_session_payload(
    base_timestamp: datetime,
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "session-1",
        "source": "claude",
        "identity_keys": ("session:claude:session-1",),
        "started_at": base_timestamp,
        "updated_at": base_timestamp,
        "ended_at": base_timestamp,
        "metadata": {"title": "Snowiki V2 Wave 1"},
        "status": "active",
        "provenance": copy.deepcopy(valid_provenance_payload),
        "source_metadata": {"workspace": "/home/k/local/snowiki"},
    }


@pytest.fixture
def valid_event_payload(
    base_timestamp: datetime,
    valid_message_payload: dict[str, object],
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "event-1",
        "session_id": "session-1",
        "source": "claude",
        "identity_keys": ("event:claude:session-1:event-1",),
        "type": "message",
        "timestamp": base_timestamp,
        "content": copy.deepcopy(valid_message_payload),
        "provenance": copy.deepcopy(valid_provenance_payload),
        "parent_event_id": None,
        "artifact_ids": ("artifact-1",),
        "source_metadata": {"event_kind": "assistant_message"},
    }


@pytest.fixture
def valid_ingest_status_payload(
    base_timestamp: datetime,
    valid_provenance_payload: dict[str, object],
) -> dict[str, object]:
    return {
        "id": "ingest-session-1",
        "source": "claude",
        "identity_keys": ("ingest:claude:session-1",),
        "record_type": "session",
        "record_id": "session-1",
        "state": "normalized",
        "first_seen_at": base_timestamp,
        "last_seen_at": base_timestamp,
        "attempts": 1,
        "duplicate_of": None,
        "error": None,
        "provenance": copy.deepcopy(valid_provenance_payload),
        "source_metadata": {"ingest_run": "wave-1"},
    }


@pytest.fixture
def valid_payloads(
    valid_provenance_payload: dict[str, object],
    valid_part_payload: dict[str, object],
    valid_message_payload: dict[str, object],
    valid_artifact_payload: dict[str, object],
    valid_session_payload: dict[str, object],
    valid_event_payload: dict[str, object],
    valid_ingest_status_payload: dict[str, object],
) -> dict[SchemaModel, dict[str, object]]:
    return {
        Provenance: copy.deepcopy(valid_provenance_payload),
        Part: copy.deepcopy(valid_part_payload),
        Message: copy.deepcopy(valid_message_payload),
        Artifact: copy.deepcopy(valid_artifact_payload),
        Session: copy.deepcopy(valid_session_payload),
        Event: copy.deepcopy(valid_event_payload),
        IngestStatus: copy.deepcopy(valid_ingest_status_payload),
    }


@pytest.fixture
def valid_instances(
    valid_payloads: dict[SchemaModel, dict[str, object]],
) -> dict[SchemaModel, BaseModel]:
    return {
        model_cls: model_cls.model_validate(copy.deepcopy(payload))
        for model_cls, payload in valid_payloads.items()
    }


@pytest.fixture
def missing_identity_payloads(
    valid_payloads: dict[SchemaModel, dict[str, object]],
) -> dict[SchemaModel, dict[str, object]]:
    payloads: dict[SchemaModel, dict[str, object]] = {}
    for model_cls, payload in valid_payloads.items():
        invalid_payload = copy.deepcopy(payload)
        invalid_payload.pop("identity_keys", None)
        payloads[model_cls] = invalid_payload
    return payloads


@pytest.fixture
def empty_identity_payloads(
    valid_payloads: dict[SchemaModel, dict[str, object]],
) -> dict[SchemaModel, dict[str, object]]:
    payloads: dict[SchemaModel, dict[str, object]] = {}
    for model_cls, payload in valid_payloads.items():
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["identity_keys"] = ()
        payloads[model_cls] = invalid_payload
    return payloads


@pytest.fixture
def missing_provenance_payloads(
    valid_payloads: dict[SchemaModel, dict[str, object]],
) -> dict[SchemaModel, dict[str, object]]:
    payloads: dict[SchemaModel, dict[str, object]] = {}
    for model_cls in (Session, Event, Message, Part, Artifact, IngestStatus):
        invalid_payload = copy.deepcopy(valid_payloads[model_cls])
        invalid_payload.pop("provenance", None)
        payloads[model_cls] = invalid_payload
    return payloads
