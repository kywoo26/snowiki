from __future__ import annotations

import json
from pathlib import Path

from snowiki.dedupe.tombstone import TombstoneStore


def test_mark_deleted_persists_lookupable_tombstone(tmp_path: Path) -> None:
    store = TombstoneStore(tmp_path)

    entry = store.mark_deleted(
        record_type="message",
        identity_key="message:claude:1",
        record_id="msg-1",
        path="normalized/claude/msg-1.json",
        deleted_at="2026-04-09T12:00:00+09:00",
    )

    assert entry == {
        "deleted_at": "2026-04-09T03:00:00Z",
        "identity_key": "message:claude:1",
        "path": "normalized/claude/msg-1.json",
        "record_id": "msg-1",
        "record_type": "message",
        "status": "deleted",
    }
    assert store.lookup("message", "message:claude:1") == entry
    assert store.is_tombstoned("message", "message:claude:1") is True


def test_lookup_returns_none_for_missing_tombstone_and_updates_existing_entry(
    tmp_path: Path,
) -> None:
    store = TombstoneStore(tmp_path)

    assert store.lookup("message", "missing") is None
    assert store.is_tombstoned("message", "missing") is False

    first = store.mark_deleted(
        record_type="message",
        identity_key="message:claude:1",
        record_id="msg-1",
        path="normalized/claude/msg-1.json",
        deleted_at="2026-04-09T00:00:00Z",
    )
    second = store.mark_deleted(
        record_type="message",
        identity_key="message:claude:1",
        record_id="msg-2",
        path="normalized/claude/msg-2.json",
        deleted_at="2026-04-09T01:00:00Z",
    )

    registry = json.loads(store.tombstone_path.read_text(encoding="utf-8"))

    assert first["record_id"] == "msg-1"
    assert second["record_id"] == "msg-2"
    assert (
        registry["message"]["message:claude:1"]["path"]
        == "normalized/claude/msg-2.json"
    )
