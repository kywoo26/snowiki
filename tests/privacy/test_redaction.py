from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.privacy.gate import PrivacyGate
from snowiki.privacy.redaction import REDACTED_VALUE, redact_secrets
from snowiki.storage.normalized import NormalizedStorage


def test_redact_secrets_masks_common_secret_patterns() -> None:
    payload = {
        "api_key": "sk_live_1234567890",
        "nested": {
            "message": "authorization: Bearer abcdefghijklmnop",
            "password": "super-secret",
        },
        "text": "token=ghp_1234567890abcdef and password=hunter2",
    }

    redacted = redact_secrets(payload)

    assert redacted["api_key"] == REDACTED_VALUE
    assert redacted["nested"]["password"] == REDACTED_VALUE
    assert "abcdefghijklmnop" not in redacted["nested"]["message"]
    assert "hunter2" not in redacted["text"]
    assert "ghp_1234567890abcdef" not in redacted["text"]


def test_normalized_storage_redacts_sensitive_values_automatically(
    tmp_path: Path,
) -> None:
    storage = NormalizedStorage(tmp_path)
    raw_ref: dict[str, object] = {
        "sha256": "abc123",
        "path": "raw/claude/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }

    result = storage.store_record(
        source_type="claude",
        record_type="message",
        record_id="msg-1",
        payload={
            "password": "open-sesame",
            "text": "api_key=sk_live_1234567890",
        },
        raw_ref=raw_ref,
        recorded_at="2026-04-08T12:00:00Z",
    )

    record = storage.read_record(result["path"])

    assert record["password"] == REDACTED_VALUE
    assert "sk_live_1234567890" not in str(record["text"])


def test_privacy_gate_blocks_excluded_sources() -> None:
    gate = PrivacyGate()

    assert gate.exclusion_reason("/tmp/project/.env") == (
        "sensitive path excluded from ingest: .env"
    )
    with pytest.raises(ValueError, match="sensitive path excluded"):
        gate.ensure_allowed_source("/tmp/project/.env")


def test_privacy_gate_prepare_payload_redacts_allowed_payloads() -> None:
    gate = PrivacyGate()

    prepared = gate.prepare_payload(
        {"token": "abc123", "nested": {"password": "secret"}},
        source_path="/tmp/project/notes.jsonl",
    )

    assert prepared == {
        "token": REDACTED_VALUE,
        "nested": {"password": REDACTED_VALUE},
    }
    assert gate.prepare_payload({"token": "abc123"}) == {"token": REDACTED_VALUE}
