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


def test_store_markdown_document_uses_latest_only_path(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/markdown/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }

    result = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="README.md",
        payload={
            "title": "Readme",
            "summary": "",
            "text": "# Readme",
            "frontmatter": {},
            "promoted_frontmatter": {},
            "reserved_frontmatter": {},
            "source_path": "/repo/docs/README.md",
            "source_root": "/repo/docs",
            "relative_path": "README.md",
            "content_hash": "abc123",
            "source_metadata": {"extension": ".md", "size": 42},
        },
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )

    assert result["status"] == "inserted"
    assert result["path"].startswith("normalized/markdown/documents/")
    assert result["path"].endswith(".json")
    assert result["record"]["source_type"] == "markdown"
    assert result["record"]["record_type"] == "document"
    assert result["record"]["content_hash"] == "abc123"
    assert storage.read_record(result["path"]) == result["record"]


def test_store_markdown_document_reports_unchanged_then_updated(
    tmp_path: Path,
) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/markdown/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }
    payload: dict[str, object] = {
        "title": "Readme",
        "summary": "",
        "text": "# Readme",
        "frontmatter": {},
        "promoted_frontmatter": {},
        "reserved_frontmatter": {},
        "source_path": "/repo/docs/README.md",
        "source_root": "/repo/docs",
        "relative_path": "README.md",
        "content_hash": "abc123",
        "source_metadata": {"extension": ".md", "size": 42},
    }

    first = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="README.md",
        payload=payload,
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )
    second = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="README.md",
        payload=payload,
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )
    updated = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="README.md",
        payload={**payload, "content_hash": "def456", "text": "# Changed"},
        raw_ref={**raw_ref, "sha256": "def456", "path": "raw/markdown/de/f456"},
        recorded_at="2026-04-08T12:01:00Z",
    )

    assert first["status"] == "inserted"
    assert second["status"] == "unchanged"
    assert updated["status"] == "updated"
    assert first["path"] == second["path"] == updated["path"]
    assert updated["record"]["content_hash"] == "def456"


def test_store_markdown_document_requires_source_identity(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/markdown/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }

    with pytest.raises(ValueError, match="source_root is required"):
        _ = storage.store_markdown_document(
            source_root="",
            relative_path="README.md",
            payload={"content_hash": "abc123"},
            raw_ref=raw_ref,
            recorded_at="2026-04-08T12:00:00Z",
        )
    with pytest.raises(ValueError, match="relative_path is required"):
        _ = storage.store_markdown_document(
            source_root="/repo/docs",
            relative_path="",
            payload={"content_hash": "abc123"},
            raw_ref=raw_ref,
            recorded_at="2026-04-08T12:00:00Z",
        )


def test_read_record_requires_json_object(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    record_path = tmp_path / "normalized" / "record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match="must be a JSON object"):
        _ = storage.read_record(record_path)


def test_store_markdown_document_treats_non_string_existing_hash_as_update(
    tmp_path: Path,
) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/markdown/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }
    record_id = storage.deterministic_id("markdown_document", "/repo/docs", "README.md")
    existing_path = storage.path_for_markdown_document(record_id)
    existing_path.parent.mkdir(parents=True)
    existing_path.write_text('{"content_hash": null}', encoding="utf-8")

    result = storage.store_markdown_document(
        source_root="/repo/docs",
        relative_path="README.md",
        payload={"content_hash": "abc123"},
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )

    assert result["status"] == "inserted"
    assert result["record"]["content_hash"] == "abc123"
