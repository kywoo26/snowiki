from __future__ import annotations

from typing import TypedDict

from .parser import ClaudeRecord, ClaudeValue


class PartPayload(TypedDict):
    """Normalized Claude message part payload."""

    type: str
    text: str | None
    data: dict[str, ClaudeValue]
    artifact_id: str | None
    mime_type: str | None


def extract_message_part_payloads(
    record: ClaudeRecord,
    attachments_by_id: dict[str, ClaudeRecord],
) -> list[PartPayload]:
    """Extract normalized part payloads from a Claude message record."""
    payloads: list[PartPayload] = []

    for block in _as_list(record.get("content")):
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")
        if block_type == "text":
            payloads.append(
                {
                    "type": "text",
                    "text": _string_or_none(block.get("text")),
                    "data": {},
                    "artifact_id": None,
                    "mime_type": None,
                }
            )
            continue

        if block_type == "thinking":
            payloads.append(
                {
                    "type": "thinking",
                    "text": _string_or_none(block.get("thinking") or block.get("text")),
                    "data": {"signature": block.get("signature")},
                    "artifact_id": None,
                    "mime_type": None,
                }
            )
            continue

        payloads.append(
            {
                "type": str(block_type or "unknown"),
                "text": None,
                "data": dict(block),
                "artifact_id": None,
                "mime_type": None,
            }
        )

    for attachment_id in _as_list(record.get("attachments")):
        if not isinstance(attachment_id, str):
            continue
        attachment = attachments_by_id.get(attachment_id, {})
        payloads.append(
            {
                "type": "attachment_reference",
                "artifact_id": attachment_id,
                "data": {
                    "attachment_id": attachment_id,
                    "file_name": attachment.get("file_name"),
                    "mime_type": attachment.get("mime_type"),
                },
                "text": None,
                "mime_type": _string_or_none(attachment.get("mime_type")),
            }
        )

    if payloads:
        return payloads

    return [
        {
            "type": "text",
            "text": "",
            "data": {},
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def extract_tool_use_part_payloads(record: ClaudeRecord) -> list[PartPayload]:
    """Extract a normalized tool-use payload."""
    return [
        {
            "type": "tool_use",
            "text": None,
            "data": {
                "tool_name": record.get("tool_name"),
                "arguments": record.get("arguments", {}),
            },
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def extract_tool_result_part_payloads(record: ClaudeRecord) -> list[PartPayload]:
    """Extract normalized payloads from a Claude tool-result record."""
    payloads: list[PartPayload] = []

    stdout = _string_or_none(record.get("stdout"))
    stderr = _string_or_none(record.get("stderr"))
    if stdout is not None:
        payloads.append(
            {
                "type": "tool_stdout",
                "text": stdout,
                "data": {},
                "artifact_id": None,
                "mime_type": None,
            }
        )
    if stderr:
        payloads.append(
            {
                "type": "tool_stderr",
                "text": stderr,
                "data": {},
                "artifact_id": None,
                "mime_type": None,
            }
        )

    payloads.append(
        {
            "type": "tool_result",
            "text": None,
            "data": {
                "tool_event_id": record.get("tool_event_id"),
                "is_error": record.get("is_error", False),
            },
            "artifact_id": None,
            "mime_type": None,
        }
    )
    return payloads


def extract_attachment_part_payloads(record: ClaudeRecord) -> list[PartPayload]:
    """Extract a normalized payload from a Claude attachment record."""
    return [
        {
            "type": "attachment",
            "text": None,
            "artifact_id": _string_or_none(record.get("attachment_id")),
            "data": {
                "attachment_id": record.get("attachment_id"),
                "file_name": record.get("file_name"),
                "mime_type": record.get("mime_type"),
                "size_bytes": record.get("size_bytes"),
                "sha256": record.get("sha256"),
                "uri": record.get("uri"),
            },
            "mime_type": _string_or_none(record.get("mime_type")),
        }
    ]


def extract_sidechain_part_payloads(record: ClaudeRecord) -> list[PartPayload]:
    """Extract a normalized payload from a Claude sidechain record."""
    return [
        {
            "type": "sidechain",
            "text": _string_or_none(record.get("summary")) or "",
            "data": {
                "branch_id": record.get("branch_id"),
                "parent_message_id": record.get("parent_message_id"),
            },
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def extract_resume_part_payloads(record: ClaudeRecord) -> list[PartPayload]:
    """Extract a normalized payload from a Claude resume record."""
    return [
        {
            "type": "resume",
            "text": _string_or_none(record.get("reason")) or "",
            "data": {"previous_session_id": record.get("previous_session_id")},
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def _as_list(value: ClaudeValue) -> list[ClaudeValue]:
    if isinstance(value, list):
        return value
    return []


def _string_or_none(value: ClaudeValue) -> str | None:
    return value if isinstance(value, str) else None
