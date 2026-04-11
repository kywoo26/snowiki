from __future__ import annotations

from pathlib import Path

from snowiki.storage.dedupe import DedupeEngine


def test_stable_id_is_deterministic(tmp_path: Path) -> None:
    dedupe = DedupeEngine(tmp_path)

    first = dedupe.stable_id("message", "claude", "session-1", {"role": "assistant"})
    second = dedupe.stable_id("message", "claude", "session-1", {"role": "assistant"})

    assert first == second
    assert first.startswith("message_")


def test_register_and_lookup_raw_entries(tmp_path: Path) -> None:
    dedupe = DedupeEngine(tmp_path)
    raw_ref = {
        "sha256": "abc123",
        "path": "raw/claude/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }

    registered, duplicate = dedupe.register_raw(raw_ref)
    again, duplicate_again = dedupe.register_raw(raw_ref)

    assert duplicate is False
    assert duplicate_again is True
    assert registered == raw_ref
    assert again == raw_ref
    assert dedupe.lookup_raw("abc123") == raw_ref


def test_identity_keys_can_be_built_or_supplied(tmp_path: Path) -> None:
    dedupe = DedupeEngine(tmp_path)

    generated = dedupe.build_identity_key(
        record_type="message",
        source_type="claude",
        payload={"id": "message-1", "role": "assistant"},
    )
    explicit = dedupe.build_identity_key(
        record_type="message",
        source_type="claude",
        payload={"id": "message-1", "role": "assistant"},
        identity_key="message:claude:message-1",
    )

    assert len(generated) == 64
    assert explicit == "message:claude:message-1"


def test_register_and_lookup_identity_entries(tmp_path: Path) -> None:
    dedupe = DedupeEngine(tmp_path)

    registered, duplicate = dedupe.register_identity(
        record_type="message",
        identity_key="message:claude:message-1",
        record_id="message-1",
        path="normalized/claude/2026/04/08/message-1.json",
    )
    again, duplicate_again = dedupe.register_identity(
        record_type="message",
        identity_key="message:claude:message-1",
        record_id="message-1",
        path="normalized/claude/2026/04/08/message-1.json",
    )

    assert duplicate is False
    assert duplicate_again is True
    assert registered == again
    assert dedupe.lookup_identity("message", "message:claude:message-1") == registered
