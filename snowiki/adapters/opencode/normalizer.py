from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from snowiki.schema import (
    Event,
    IngestState,
    IngestStatus,
    Message,
    Part,
    Provenance,
    Session,
    SessionStatus,
)

from .db import checksum_sha256
from .extractor import extract_part_payload
from .failures import (
    OpenCodeLockedSourceError,
    OpenCodePartialSourceError,
)
from .parser import ParsedSessionSource, RawMessage, RawPart
from .todos import (
    iter_diff_events,
    iter_system_reminders,
    todo_event_metadata,
)

SOURCE_NAME = "opencode"


@dataclass(frozen=True, slots=True)
class NormalizedOpenCodeSession:
    session: Session | None
    messages: tuple[Message, ...]
    events: tuple[Event, ...]
    ingest_status: IngestStatus
    error: str | None = None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _path_uri(path: Path) -> str:
    return path.expanduser().resolve().as_uri()


def _provenance(
    *,
    db_path: Path,
    checksum: str | None,
    raw_id: str,
    raw_kind: str,
    captured_at: datetime,
    locator: dict[str, Any],
    source_metadata: dict[str, Any] | None = None,
) -> Provenance:
    return Provenance(
        id=f"prov-opencode-{raw_kind}-{raw_id}",
        source=SOURCE_NAME,
        identity_keys=(f"raw:{SOURCE_NAME}:{raw_kind}:{raw_id}",),
        raw_uri=_path_uri(db_path),
        raw_id=raw_id,
        raw_kind=raw_kind,
        captured_at=captured_at,
        locator=locator,
        checksum_sha256=checksum,
        source_metadata=source_metadata,
    )


def _session_status(source: ParsedSessionSource) -> SessionStatus:
    if source.session.time_archived is not None:
        return SessionStatus.ARCHIVED
    if source.session.time_compacting is not None:
        return SessionStatus.INCOMPLETE
    return SessionStatus.ACTIVE


def _build_part(
    raw_part: RawPart,
    *,
    db_path: Path,
    checksum: str | None,
) -> Part:
    extracted = extract_part_payload(raw_part)
    return Part(
        id=raw_part.id,
        message_id=raw_part.message_id,
        source=SOURCE_NAME,
        identity_keys=(
            f"part:{SOURCE_NAME}:{raw_part.session_id}:{raw_part.message_id}:{raw_part.id}",
        ),
        type=extracted.type,
        index=0,
        text=extracted.text,
        data=extracted.data,
        mime_type=extracted.mime_type,
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=raw_part.id,
            raw_kind="sqlite_part",
            captured_at=raw_part.time_updated,
            locator={
                "table": "part",
                "id": raw_part.id,
                "message_id": raw_part.message_id,
            },
        ),
        source_metadata={
            "time_created": raw_part.time_created.isoformat(),
            "time_updated": raw_part.time_updated.isoformat(),
        },
    )


def _build_message(
    raw_message: RawMessage,
    *,
    parts: tuple[RawPart, ...],
    db_path: Path,
    checksum: str | None,
) -> Message:
    canonical_parts = tuple(
        Part.model_validate(
            {
                **_build_part(
                    raw_part, db_path=db_path, checksum=checksum
                ).model_dump(),
                "index": index,
            }
        )
        for index, raw_part in enumerate(parts)
    )
    return Message(
        id=raw_message.id,
        session_id=raw_message.session_id,
        source=SOURCE_NAME,
        identity_keys=(
            f"message:{SOURCE_NAME}:{raw_message.session_id}:{raw_message.id}",
        ),
        role=str(raw_message.data.get("role", "unknown")),
        created_at=raw_message.time_created,
        parts=canonical_parts,
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=raw_message.id,
            raw_kind="sqlite_message",
            captured_at=raw_message.time_updated,
            locator={
                "table": "message",
                "id": raw_message.id,
                "session_id": raw_message.session_id,
            },
        ),
        source_metadata=raw_message.data,
    )


def _build_message_event(
    message: Message, *, db_path: Path, checksum: str | None
) -> Event:
    return Event(
        id=f"event-opencode-message-{message.id}",
        session_id=message.session_id,
        source=SOURCE_NAME,
        identity_keys=(
            f"event:{SOURCE_NAME}:{message.session_id}:message:{message.id}",
        ),
        type="message",
        timestamp=message.created_at,
        content=message,
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=message.id,
            raw_kind="message_event",
            captured_at=message.created_at,
            locator={"table": "message", "id": message.id},
        ),
        source_metadata={"event_kind": f"{message.role}_message"},
    )


def _simple_event(
    *,
    event_id: str,
    session_id: str,
    event_type: str,
    timestamp: datetime,
    db_path: Path,
    checksum: str | None,
    raw_kind: str,
    source_metadata: dict[str, Any],
) -> Event:
    return Event(
        id=event_id,
        session_id=session_id,
        source=SOURCE_NAME,
        identity_keys=(f"event:{SOURCE_NAME}:{session_id}:{event_type}:{event_id}",),
        type=event_type,
        timestamp=timestamp,
        content=None,
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=event_id,
            raw_kind=raw_kind,
            captured_at=timestamp,
            locator={"kind": raw_kind, "event_id": event_id},
        ),
        source_metadata=source_metadata,
    )


def normalize_session_source(source: ParsedSessionSource) -> NormalizedOpenCodeSession:
    db_path = source.path
    checksum = checksum_sha256(db_path)

    messages = tuple(
        _build_message(
            message,
            parts=source.parts_by_message.get(message.id, ()),
            db_path=db_path,
            checksum=checksum,
        )
        for message in source.messages
    )

    session = Session(
        id=source.session.id,
        source=SOURCE_NAME,
        identity_keys=(f"session:{SOURCE_NAME}:{source.session.id}",),
        started_at=source.session.time_created,
        updated_at=source.session.time_updated,
        ended_at=source.session.time_archived,
        metadata={
            "title": source.session.title,
            "slug": source.session.slug,
            "version": source.session.version,
            "directory": source.session.directory,
        },
        status=_session_status(source),
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=source.session.id,
            raw_kind="sqlite_session",
            captured_at=source.session.time_updated,
            locator={"table": "session", "id": source.session.id},
        ),
        source_metadata={
            "parent_id": source.session.parent_id,
            "share_url": source.session.share_url,
            "permission": source.session.permission,
            "summary_additions": source.session.summary_additions,
            "summary_deletions": source.session.summary_deletions,
            "summary_files": source.session.summary_files,
            "summary_diffs": source.session.summary_diffs,
            "project": source.project.row if source.project is not None else None,
            "workspace": source.workspace.row if source.workspace is not None else None,
        },
    )

    events: list[Event] = [
        _build_message_event(message, db_path=db_path, checksum=checksum)
        for message in messages
    ]

    for raw_todo in source.todos:
        events.append(
            _simple_event(
                event_id=f"event-opencode-todo-{source.session.id}-{raw_todo.position}",
                session_id=source.session.id,
                event_type="todo",
                timestamp=raw_todo.time_updated,
                db_path=db_path,
                checksum=checksum,
                raw_kind="sqlite_todo",
                source_metadata=todo_event_metadata(raw_todo),
            )
        )

    for suffix, timestamp_text, metadata in iter_diff_events(source):
        events.append(
            _simple_event(
                event_id=f"event-opencode-diff-{suffix}",
                session_id=source.session.id,
                event_type="diff",
                timestamp=datetime.fromisoformat(timestamp_text),
                db_path=db_path,
                checksum=checksum,
                raw_kind="derived_diff",
                source_metadata=metadata,
            )
        )

    for suffix, timestamp_text, metadata in iter_system_reminders(source.messages):
        events.append(
            _simple_event(
                event_id=f"event-opencode-system-{suffix}",
                session_id=source.session.id,
                event_type="system_reminder",
                timestamp=datetime.fromisoformat(timestamp_text),
                db_path=db_path,
                checksum=checksum,
                raw_kind="derived_system_reminder",
                source_metadata=metadata,
            )
        )

    events.sort(key=lambda event: (event.timestamp, event.id))

    ingest_status = IngestStatus(
        id=f"ingest-opencode-{source.session.id}",
        source=SOURCE_NAME,
        identity_keys=(f"ingest:{SOURCE_NAME}:{source.session.id}",),
        record_type="session",
        record_id=source.session.id,
        state=IngestState.NORMALIZED,
        first_seen_at=source.session.time_created,
        last_seen_at=source.session.time_updated,
        attempts=1,
        duplicate_of=None,
        error=None,
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=source.session.id,
            raw_kind="sqlite_ingest",
            captured_at=source.session.time_updated,
            locator={"table": "session", "id": source.session.id},
        ),
        source_metadata={"message_count": len(messages), "event_count": len(events)},
    )

    return NormalizedOpenCodeSession(
        session=session,
        messages=messages,
        events=tuple(events),
        ingest_status=ingest_status,
    )


def build_failure_result(
    *,
    db_path: Path,
    session_id: str | None,
    error: OpenCodeLockedSourceError | OpenCodePartialSourceError,
) -> NormalizedOpenCodeSession:
    now = _now()
    record_id = session_id or db_path.name
    state = (
        IngestState.FAILED
        if isinstance(error, OpenCodeLockedSourceError)
        else IngestState.QUARANTINED
    )
    checksum = checksum_sha256(db_path)
    ingest_status = IngestStatus(
        id=f"ingest-opencode-failure-{record_id}",
        source=SOURCE_NAME,
        identity_keys=(f"ingest:{SOURCE_NAME}:failure:{record_id}",),
        record_type="session",
        record_id=record_id,
        state=state,
        first_seen_at=now,
        last_seen_at=now,
        attempts=1,
        duplicate_of=None,
        error=str(error),
        provenance=_provenance(
            db_path=db_path,
            checksum=checksum,
            raw_id=record_id,
            raw_kind="sqlite_failure",
            captured_at=now,
            locator={"path": str(db_path)},
            source_metadata={"error_type": error.__class__.__name__},
        ),
        source_metadata={"path": str(db_path), "error_type": error.__class__.__name__},
    )
    return NormalizedOpenCodeSession(
        session=None,
        messages=(),
        events=(),
        ingest_status=ingest_status,
        error=str(error),
    )


__all__ = [
    "NormalizedOpenCodeSession",
    "SOURCE_NAME",
    "build_failure_result",
    "normalize_session_source",
]
