from __future__ import annotations

from pathlib import Path

from snowiki.adapters import parse_claude_jsonl
from snowiki.adapters.claude.extractor import (
    extract_attachment_part_payloads,
    extract_message_part_payloads,
    extract_resume_part_payloads,
    extract_sidechain_part_payloads,
    extract_tool_result_part_payloads,
    extract_tool_use_part_payloads,
)


def test_parser_preserves_current_fixture_shape(claude_fixture_dir: Path) -> None:
    records = parse_claude_jsonl(claude_fixture_dir / "basic.jsonl")
    user_message = records[1].get("message")
    assistant_message = records[2].get("message")

    assert isinstance(user_message, dict)
    assert isinstance(assistant_message, dict)

    assert [record["record_type"] for record in records] == [
        "system",
        "user",
        "assistant",
    ]
    assert records[0]["sessionId"] == "claude-basic-session"
    assert user_message["role"] == "user"
    assert assistant_message["role"] == "assistant"


def test_extract_message_part_payloads_handles_text_thinking_unknown_and_attachments() -> (
    None
):
    payloads = extract_message_part_payloads(
        {
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "thinking", "thinking": "plan", "signature": "sig-1"},
                {"type": "image", "url": "file:///tmp/image.png"},
            ],
            "attachments": ["att-1", 42, "att-2"],
        },
        {
            "att-1": {"file_name": "notes.md", "mime_type": "text/markdown"},
            "att-2": {"file_name": "queries.csv", "mime_type": "text/csv"},
        },
    )

    assert payloads == [
        {
            "type": "text",
            "text": "hello",
            "data": {},
            "artifact_id": None,
            "mime_type": None,
        },
        {
            "type": "thinking",
            "text": "plan",
            "data": {"signature": "sig-1"},
            "artifact_id": None,
            "mime_type": None,
        },
        {
            "type": "image",
            "text": None,
            "data": {"type": "image", "url": "file:///tmp/image.png"},
            "artifact_id": None,
            "mime_type": None,
        },
        {
            "type": "attachment_reference",
            "text": None,
            "artifact_id": "att-1",
            "data": {
                "attachment_id": "att-1",
                "file_name": "notes.md",
                "mime_type": "text/markdown",
            },
            "mime_type": "text/markdown",
        },
        {
            "type": "attachment_reference",
            "text": None,
            "artifact_id": "att-2",
            "data": {
                "attachment_id": "att-2",
                "file_name": "queries.csv",
                "mime_type": "text/csv",
            },
            "mime_type": "text/csv",
        },
    ]


def test_extract_message_part_payloads_returns_empty_text_when_no_parts_exist() -> None:
    assert extract_message_part_payloads({}, {}) == [
        {
            "type": "text",
            "text": "",
            "data": {},
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def test_extract_tool_payload_helpers_cover_stdout_stderr_and_defaults() -> None:
    assert extract_tool_use_part_payloads(
        {"tool_name": "bash", "arguments": {"command": "uv run pytest"}}
    ) == [
        {
            "type": "tool_use",
            "text": None,
            "data": {"tool_name": "bash", "arguments": {"command": "uv run pytest"}},
            "artifact_id": None,
            "mime_type": None,
        }
    ]
    assert extract_tool_result_part_payloads(
        {"stdout": "ok", "stderr": "warn", "tool_event_id": "tool-1", "is_error": True}
    ) == [
        {
            "type": "tool_stdout",
            "text": "ok",
            "data": {},
            "artifact_id": None,
            "mime_type": None,
        },
        {
            "type": "tool_stderr",
            "text": "warn",
            "data": {},
            "artifact_id": None,
            "mime_type": None,
        },
        {
            "type": "tool_result",
            "text": None,
            "data": {"tool_event_id": "tool-1", "is_error": True},
            "artifact_id": None,
            "mime_type": None,
        },
    ]
    assert extract_tool_result_part_payloads({"stderr": "", "tool_event_id": None}) == [
        {
            "type": "tool_result",
            "text": None,
            "data": {"tool_event_id": None, "is_error": False},
            "artifact_id": None,
            "mime_type": None,
        }
    ]


def test_extract_attachment_sidechain_and_resume_payload_helpers() -> None:
    assert extract_attachment_part_payloads(
        {
            "attachment_id": "att-1",
            "file_name": "design-notes.md",
            "mime_type": "text/markdown",
            "size_bytes": 412,
            "sha256": "abc123",
            "uri": "file:///tmp/design-notes.md",
        }
    ) == [
        {
            "type": "attachment",
            "text": None,
            "artifact_id": "att-1",
            "data": {
                "attachment_id": "att-1",
                "file_name": "design-notes.md",
                "mime_type": "text/markdown",
                "size_bytes": 412,
                "sha256": "abc123",
                "uri": "file:///tmp/design-notes.md",
            },
            "mime_type": "text/markdown",
        }
    ]
    assert extract_sidechain_part_payloads(
        {
            "summary": "branch summary",
            "branch_id": "branch-a",
            "parent_message_id": "msg-1",
        }
    ) == [
        {
            "type": "sidechain",
            "text": "branch summary",
            "data": {"branch_id": "branch-a", "parent_message_id": "msg-1"},
            "artifact_id": None,
            "mime_type": None,
        }
    ]
    assert extract_resume_part_payloads(
        {"reason": "continuing work", "previous_session_id": "session-1"}
    ) == [
        {
            "type": "resume",
            "text": "continuing work",
            "data": {"previous_session_id": "session-1"},
            "artifact_id": None,
            "mime_type": None,
        }
    ]
