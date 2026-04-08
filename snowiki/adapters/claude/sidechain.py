from __future__ import annotations

from .parser import ClaudeRecord, ClaudeValue


def collect_sidechain_metadata(
    records: list[ClaudeRecord],
) -> tuple[dict[str, ClaudeValue], ...]:
    """Collect sidechain metadata for a normalized Claude session."""
    sidechains: list[dict[str, ClaudeValue]] = []
    for record in records:
        if record.get("record_type") != "sidechain":
            continue

        sidechains.append(
            {
                "event_id": record.get("event_id"),
                "parent_message_id": record.get("parent_message_id"),
                "branch_id": record.get("branch_id"),
                "summary": record.get("summary"),
                "created_at": record.get("created_at"),
                "line_number": record.get("_line_number"),
            }
        )

    return tuple(sidechains)


def extract_branch_metadata(record: ClaudeRecord) -> dict[str, ClaudeValue]:
    """Extract branch-related metadata fields from a Claude record."""
    metadata: dict[str, ClaudeValue] = {}
    for key in (
        "branch_id",
        "parent_message_id",
        "summary",
        "previous_session_id",
        "reason",
    ):
        if key in record and record[key] is not None:
            metadata[key] = record[key]
    return metadata


def resolve_parent_event_id(record: ClaudeRecord) -> str | None:
    """Resolve the closest parent event identifier for a Claude record."""
    for key in ("tool_event_id", "parent_message_id", "message_id"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None
