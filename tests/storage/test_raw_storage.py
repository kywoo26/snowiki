from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from snowiki.storage.raw import RawStorage


def test_store_bytes_uses_sha_addressing(tmp_path: Path) -> None:
    storage = RawStorage(tmp_path)

    result = storage.store_bytes("claude sessions", b"hello world")
    stored_path = tmp_path / str(result["path"])

    assert (
        result["sha256"]
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )
    assert result["path"] == (
        "raw/claude-sessions/b9/"
        "4d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )
    assert result["size"] == 11
    assert stored_path.read_bytes() == b"hello world"


def test_store_file_preserves_source_mtime_on_first_write(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl"
    _ = source_path.write_text("payload", encoding="utf-8")
    captured_at = datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc)
    timestamp = captured_at.timestamp()
    os.utime(source_path, (timestamp, timestamp))

    storage = RawStorage(tmp_path / "vault")
    result = storage.store_file("claude", source_path)

    stored_path = storage.root / str(result["path"])
    assert stored_path.exists()
    assert result["mtime"] == "2026-04-08T12:00:00Z"
    assert stored_path.stat().st_mtime == timestamp


def test_store_bytes_returns_existing_entry_for_duplicate_content(
    tmp_path: Path,
) -> None:
    storage = RawStorage(tmp_path)

    first = storage.store_bytes("claude", b"same content")
    second = storage.store_bytes("claude", b"same content")

    assert second == first
