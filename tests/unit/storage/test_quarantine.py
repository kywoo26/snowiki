from __future__ import annotations

import json
from pathlib import Path

from snowiki.storage.quarantine import QuarantineManager


def test_quarantine_bytes_writes_payload_and_metadata(tmp_path: Path) -> None:
    quarantine = QuarantineManager(tmp_path)

    result = quarantine.quarantine_bytes(
        source_name="session export.jsonl",
        content=b"bad payload",
        reason="invalid newline framing",
        original_path="incoming/session export.jsonl",
        timestamp="2026-04-08T12:00:00Z",
    )

    payload_path = tmp_path / str(result["payload_path"])
    metadata_path = tmp_path / str(result["metadata_path"])

    assert payload_path.read_bytes() == b"bad payload"
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == {
        "original_path": "incoming/session export.jsonl",
        "reason": "invalid newline framing",
        "source_name": "session export.jsonl",
        "timestamp": "2026-04-08T12:00:00Z",
    }


def test_quarantine_file_copies_existing_file(tmp_path: Path) -> None:
    source_path = tmp_path / "broken.txt"
    _ = source_path.write_text("broken", encoding="utf-8")
    quarantine = QuarantineManager(tmp_path / "vault")

    result = quarantine.quarantine_file(
        file_path=source_path,
        reason="encoding error",
        timestamp="2026-04-08T13:00:00Z",
    )

    payload_path = quarantine.root / str(result["payload_path"])
    assert payload_path.read_text(encoding="utf-8") == "broken"
