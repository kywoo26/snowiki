from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from snowiki.adapters.claude.extractor import (
    PartPayload,
    extract_attachment_part_payloads,
    extract_message_part_payloads,
    extract_resume_part_payloads,
    extract_sidechain_part_payloads,
    extract_tool_result_part_payloads,
    extract_tool_use_part_payloads,
)
from snowiki.adapters.claude.parser import ClaudeRecord, ClaudeValue, parse_claude_jsonl
from snowiki.adapters.claude.sidechain import (
    collect_sidechain_metadata,
    extract_branch_metadata,
    resolve_parent_event_id,
)
from snowiki.schema import Event, Message, Part, Provenance, Session, SessionStatus

SOURCE = "claude"
IGNORED_RECORD_TYPES = frozenset({"session_end"})
SUPPORTED_EVENT_TYPES = frozenset(
    {"message", "tool_use", "tool_result", "attachment", "sidechain", "resume"}
)


@dataclass(frozen=True)
class ClaudeNormalizedSession:
    """Normalized Claude session plus its event stream."""

    session: Session
    events: tuple[Event, ...]


def normalize_claude_session_file(path: str | Path) -> ClaudeNormalizedSession:
    """Normalize a Claude JSONL export into schema-backed session data.

    Args:
        path: Path to the Claude session export.

    Returns:
        Normalized session and event models.

    Raises:
        ValueError: If the export is empty or missing required fields.
    """
    source_path = Path(path)
    records = parse_claude_jsonl(source_path)

    if not records:
        raise ValueError("Claude JSONL stream is empty")

    session_record = _first_record(records, "session")
    session_id = _require_str(session_record, "session_id")
    raw_uri = source_path.resolve().as_uri()
    captured_at = _utcnow()
    attachments_by_id = _index_attachments(records)
    ignored_record_types = _collect_ignored_record_types(records)
    events = tuple(
        _normalize_event(
            record=record,
            raw_uri=raw_uri,
            session_id=session_id,
            attachments_by_id=attachments_by_id,
            captured_at=captured_at,
        )
        for record in records
        if _is_normalizable_event(record)
    )

    session = _normalize_session(
        session_record=session_record,
        records=records,
        raw_uri=raw_uri,
        captured_at=captured_at,
        ignored_record_types=ignored_record_types,
    )
    return ClaudeNormalizedSession(session=session, events=events)


def _normalize_session(
    session_record: ClaudeRecord,
    records: list[ClaudeRecord],
    raw_uri: str,
    captured_at: datetime,
    ignored_record_types: tuple[str, ...],
) -> Session:
    session_id = _require_str(session_record, "session_id")
    session_end = _last_record(records, "session_end")
    timestamps = list(_iter_timestamps(records))
    started_at = _parse_datetime(session_record["started_at"])
    updated_at = max(timestamps, default=started_at)
    ended_at = (
        _parse_datetime(session_end["ended_at"])
        if session_end is not None and "ended_at" in session_end
        else None
    )
    status_value = (
        session_end.get("status")
        if session_end is not None
        else SessionStatus.ACTIVE.value
    )
    status = SessionStatus(status_value)
    metadata = _mapping_or_empty(session_record.get("metadata"))

    source_metadata = {
        "workspace": session_record.get("workspace"),
        "resumed_from_session_id": session_record.get("resumed_from_session_id"),
        "sidechains": collect_sidechain_metadata(records),
        "ignored_record_types": ignored_record_types,
        "record_count": len(records),
    }

    return Session.model_validate(
        {
            "id": session_id,
            "source": SOURCE,
            "identity_keys": (f"session:{SOURCE}:{session_id}",),
            "started_at": started_at,
            "updated_at": updated_at,
            "ended_at": ended_at,
            "metadata": metadata,
            "status": status,
            "provenance": _build_provenance(
                raw_uri=raw_uri,
                raw_id=session_id,
                raw_kind="jsonl_session",
                captured_at=captured_at,
                line_number=_line_number_for_record(session_record),
                identity_prefix="session",
            ),
            "source_metadata": source_metadata,
        }
    )


def _normalize_event(
    record: ClaudeRecord,
    raw_uri: str,
    session_id: str,
    attachments_by_id: dict[str, ClaudeRecord],
    captured_at: datetime,
) -> Event:
    record_type = _require_str(record, "record_type")
    event_id = _event_id_for_record(record)
    timestamp = _timestamp_for_record(record)
    message_id = _message_id_for_record(record)
    message_role = _role_for_record(record)
    part_payloads = _part_payloads_for_record(record, attachments_by_id)
    message_provenance = _build_provenance(
        raw_uri=raw_uri,
        raw_id=event_id,
        raw_kind=record_type,
        captured_at=captured_at,
        line_number=_line_number_for_record(record),
        identity_prefix="message",
    )
    message = Message.model_validate(
        {
            "id": message_id,
            "session_id": session_id,
            "source": SOURCE,
            "identity_keys": (f"message:{SOURCE}:{session_id}:{message_id}",),
            "role": message_role,
            "created_at": timestamp,
            "parts": tuple(
                _normalize_part(
                    payload=payload,
                    session_id=session_id,
                    message_id=message_id,
                    raw_uri=raw_uri,
                    raw_id=event_id,
                    raw_kind=record_type,
                    line_number=_line_number_for_record(record),
                    index=index,
                    captured_at=captured_at,
                )
                for index, payload in enumerate(part_payloads)
            ),
            "provenance": message_provenance,
            "source_metadata": {
                "record_type": record_type,
                "event_id": event_id,
                **extract_branch_metadata(record),
            },
        }
    )

    artifact_ids = _artifact_ids_for_record(record)
    return Event.model_validate(
        {
            "id": event_id,
            "session_id": session_id,
            "source": SOURCE,
            "identity_keys": (f"event:{SOURCE}:{session_id}:{event_id}",),
            "type": _event_type_for_record(record),
            "timestamp": timestamp,
            "content": message,
            "provenance": _build_provenance(
                raw_uri=raw_uri,
                raw_id=event_id,
                raw_kind=record_type,
                captured_at=captured_at,
                line_number=_line_number_for_record(record),
                identity_prefix="event",
            ),
            "parent_event_id": resolve_parent_event_id(record),
            "artifact_ids": artifact_ids,
            "source_metadata": {
                "record_type": record_type,
                **extract_branch_metadata(record),
            },
        }
    )


def _normalize_part(
    payload: PartPayload,
    session_id: str,
    message_id: str,
    raw_uri: str,
    raw_id: str,
    raw_kind: str,
    line_number: int | None,
    index: int,
    captured_at: datetime,
) -> Part:
    return Part.model_validate(
        {
            "id": f"{message_id}:part:{index}",
            "message_id": message_id,
            "source": SOURCE,
            "identity_keys": (f"part:{SOURCE}:{session_id}:{message_id}:{index}",),
            "type": payload["type"],
            "index": index,
            "text": payload.get("text"),
            "data": payload.get("data"),
            "artifact_id": payload.get("artifact_id"),
            "mime_type": payload.get("mime_type"),
            "provenance": _build_provenance(
                raw_uri=raw_uri,
                raw_id=raw_id,
                raw_kind=raw_kind,
                captured_at=captured_at,
                line_number=line_number,
                identity_prefix="part",
            ),
            "source_metadata": {"record_type": raw_kind},
        }
    )


def _part_payloads_for_record(
    record: ClaudeRecord,
    attachments_by_id: dict[str, ClaudeRecord],
) -> list[PartPayload]:
    record_type = record["record_type"]
    if record_type == "message":
        return extract_message_part_payloads(record, attachments_by_id)
    if record_type == "tool_use":
        return extract_tool_use_part_payloads(record)
    if record_type == "tool_result":
        return extract_tool_result_part_payloads(record)
    if record_type == "attachment":
        return extract_attachment_part_payloads(record)
    if record_type == "sidechain":
        return extract_sidechain_part_payloads(record)
    if record_type == "resume":
        return extract_resume_part_payloads(record)
    raise ValueError(f"unsupported Claude record type: {record_type}")


def _build_provenance(
    raw_uri: str,
    raw_id: str,
    raw_kind: str,
    captured_at: datetime,
    line_number: int | None,
    identity_prefix: str,
) -> Provenance:
    return Provenance.model_validate(
        {
            "id": f"prov:{identity_prefix}:{raw_id}",
            "source": SOURCE,
            "identity_keys": (f"raw:{SOURCE}:{raw_kind}:{raw_id}",),
            "raw_uri": raw_uri,
            "raw_id": raw_id,
            "raw_kind": raw_kind,
            "captured_at": captured_at,
            "locator": {"line": line_number},
            "source_metadata": {"adapter": SOURCE},
        }
    )


def _index_attachments(records: list[ClaudeRecord]) -> dict[str, ClaudeRecord]:
    indexed: dict[str, ClaudeRecord] = {}
    for record in records:
        if record.get("record_type") != "attachment":
            continue
        attachment_id = record.get("attachment_id")
        if isinstance(attachment_id, str) and attachment_id:
            indexed[attachment_id] = record
    return indexed


def _artifact_ids_for_record(record: ClaudeRecord) -> tuple[str, ...]:
    record_type = record["record_type"]
    if record_type == "attachment":
        attachment_id = record.get("attachment_id")
        return (
            (attachment_id,) if isinstance(attachment_id, str) and attachment_id else ()
        )

    attachment_ids = record.get("attachments")
    if isinstance(attachment_ids, list):
        return tuple(item for item in attachment_ids if isinstance(item, str) and item)
    return ()


def _event_id_for_record(record: ClaudeRecord) -> str:
    for key in ("event_id", "message_id", "attachment_id"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    if record.get("record_type") == "resume":
        session_id = _require_str(record, "session_id")
        line_number = record.get("_line_number")
        return f"{session_id}:resume:{line_number}"
    raise ValueError(f"Claude record is missing an event identifier: {record}")


def _message_id_for_record(record: ClaudeRecord) -> str:
    record_type = record["record_type"]
    if record_type == "message":
        return _require_str(record, "message_id")
    return f"{_event_id_for_record(record)}:message"


def _role_for_record(record: ClaudeRecord) -> str:
    if record["record_type"] == "message":
        return _require_str(record, "role")
    if record["record_type"] == "tool_use":
        return "assistant"
    if record["record_type"] == "attachment":
        return "user"
    return "system"


def _event_type_for_record(record: ClaudeRecord) -> str:
    if record["record_type"] == "message":
        return _require_str(record, "role")
    return _require_str(record, "record_type")


def _timestamp_for_record(record: ClaudeRecord) -> datetime:
    for key in ("created_at", "ended_at", "started_at"):
        value = record.get(key)
        if value is not None:
            return _parse_datetime(value)
    raise ValueError(f"Claude record is missing a timestamp: {record}")


def _collect_ignored_record_types(records: list[ClaudeRecord]) -> tuple[str, ...]:
    ignored = sorted(
        {
            str(record.get("record_type"))
            for record in records
            if str(record.get("record_type")) not in SUPPORTED_EVENT_TYPES
            and str(record.get("record_type")) not in {"session", *IGNORED_RECORD_TYPES}
        }
    )
    return tuple(ignored)


def _is_normalizable_event(record: ClaudeRecord) -> bool:
    return record.get("record_type") in SUPPORTED_EVENT_TYPES


def _first_record(records: Iterable[ClaudeRecord], record_type: str) -> ClaudeRecord:
    for record in records:
        if record.get("record_type") == record_type:
            return record
    raise ValueError(f"missing Claude {record_type} record")


def _last_record(
    records: Iterable[ClaudeRecord], record_type: str
) -> ClaudeRecord | None:
    last: ClaudeRecord | None = None
    for record in records:
        if record.get("record_type") == record_type:
            last = record
    return last


def _iter_timestamps(records: Iterable[ClaudeRecord]) -> Iterable[datetime]:
    for record in records:
        for key in ("created_at", "ended_at", "started_at"):
            value = record.get(key)
            if value is not None:
                yield _parse_datetime(value)
                break


def _parse_datetime(value: ClaudeValue) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"expected ISO timestamp, got {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_str(record: ClaudeRecord, key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Claude record field {key!r} must be a non-empty string")
    return value


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _line_number_for_record(record: ClaudeRecord) -> int | None:
    value = record.get("_line_number")
    return value if isinstance(value, int) else None


def _mapping_or_empty(value: ClaudeValue) -> dict[str, ClaudeValue]:
    return dict(value) if isinstance(value, dict) else {}
