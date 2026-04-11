from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .parser import (
    ParsedSessionSource,
    RawMessage,
    RawTodo,
)


def todo_event_metadata(raw_todo: RawTodo) -> dict[str, Any]:
    return {
        "content": raw_todo.content,
        "status": raw_todo.status,
        "priority": raw_todo.priority,
        "position": raw_todo.position,
        "time_created": raw_todo.time_created.isoformat(),
        "time_updated": raw_todo.time_updated.isoformat(),
    }


def iter_diff_events(
    source: ParsedSessionSource,
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    summary_diffs = source.session.summary_diffs
    if isinstance(summary_diffs, list):
        for index, diff in enumerate(summary_diffs):
            if isinstance(diff, dict):
                yield (
                    f"summary-{index}",
                    source.session.time_updated.isoformat(),
                    {"origin": "session.summary_diffs", **diff},
                )

    for message in source.messages:
        diffs = message.data.get("summary")
        if isinstance(diffs, dict):
            entries = diffs.get("diffs")
            if isinstance(entries, list):
                for index, entry in enumerate(entries):
                    if isinstance(entry, dict):
                        yield (
                            f"message-{message.id}-{index}",
                            message.time_updated.isoformat(),
                            {
                                "origin": "message.summary.diffs",
                                "message_id": message.id,
                                **entry,
                            },
                        )

    for message in source.messages:
        for part in source.parts_by_message.get(message.id, ()):
            if part.data.get("type") == "patch":
                yield (
                    part.id,
                    part.time_updated.isoformat(),
                    {"origin": "part.patch", "message_id": message.id, **part.data},
                )


def iter_system_reminders(
    messages: Iterable[RawMessage],
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    for message in messages:
        system_text = message.data.get("system")
        if isinstance(system_text, str) and system_text.strip():
            yield (
                message.id,
                message.time_created.isoformat(),
                {"message_id": message.id, "field": "system", "text": system_text},
            )

        reminder = message.data.get("systemReminder")
        if isinstance(reminder, str) and reminder.strip():
            yield (
                message.id,
                message.time_updated.isoformat(),
                {"message_id": message.id, "field": "systemReminder", "text": reminder},
            )


__all__ = ["iter_diff_events", "iter_system_reminders", "todo_event_metadata"]
