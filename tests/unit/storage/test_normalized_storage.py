from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.storage.normalized import NormalizedStorage


def test_store_record_writes_normalized_json_with_provenance(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/claude/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }

    result = storage.store_record(
        source_type="claude session",
        record_type="message",
        record_id="msg-1",
        payload={"role": "assistant", "text": "hello"},
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )

    assert result["id"] == "msg-1"
    assert result["path"] == "normalized/claude-session/2026/04/08/msg-1.json"
    assert result["record"]["raw_ref"] == raw_ref
    assert result["record"]["provenance"] == {
        "link_chain": ["normalized", "raw"],
        "raw_refs": [raw_ref],
    }
    assert storage.read_record(result["path"]) == result["record"]


def test_store_message_delegates_to_store_record(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "def456",
        "path": "raw/claude/de/f456",
        "size": 12,
        "mtime": "2026-04-08T13:00:00Z",
    }

    result = storage.store_message(
        source_type="claude",
        record_id="message-1",
        message={"role": "user"},
        raw_ref=raw_ref,
        recorded_at="2026-04-08T13:00:00Z",
    )

    assert result["record"]["record_type"] == "message"
    assert result["record"]["source_type"] == "claude"
    assert result["record"]["role"] == "user"


def test_store_record_requires_record_id(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)

    with pytest.raises(ValueError, match="record_id is required"):
        _ = storage.store_record(
            source_type="claude",
            record_type="message",
            record_id="",
            payload={},
            raw_ref={
                "sha256": "abc123",
                "path": "raw/claude/ab/c123",
                "size": 1,
                "mtime": "2026-04-08T12:00:00Z",
            },
            recorded_at="2026-04-08T12:00:00Z",
        )
