from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.storage.provenance import (
    ProvenanceTracker,
    dedupe_raw_refs,
    normalize_raw_refs,
    raw_refs_from_record,
)


def test_raw_refs_from_record_collects_supported_shapes_once() -> None:
    first = {
        "sha256": "abc123",
        "path": "raw/markdown/ab/c123",
        "size": 42,
        "mtime": "2026-04-08T12:00:00Z",
    }
    second = {
        "sha256": "def456",
        "path": "raw/markdown/de/f456",
        "size": 12,
        "mtime": "2026-04-08T12:01:00Z",
    }

    refs = raw_refs_from_record(
        {
            "raw_ref": first,
            "raw_refs": [first, "skip", second],
            "provenance": {"raw_refs": [second, {"path": "raw/manual/path.md"}]},
        }
    )

    assert refs == [first, second, {"path": "raw/manual/path.md"}]


def test_raw_refs_from_record_normalizes_mapping_keys() -> None:
    refs = raw_refs_from_record(
        {
            "provenance": {
                "raw_refs": [
                    {
                        b"sha256": "abc123",
                        "path": "raw/source.jsonl",
                    }
                ]
            }
        }
    )

    assert refs == [{"b'sha256'": "abc123", "path": "raw/source.jsonl"}]


def test_normalize_raw_refs_requires_complete_raw_refs() -> None:
    with pytest.raises(ValueError, match="raw_ref must include"):
        _ = normalize_raw_refs({"path": "raw/source.jsonl"})


def test_dedupe_raw_refs_uses_provenance_identity_with_optional_sort() -> None:
    refs = dedupe_raw_refs(
        [
            {"sha256": "b", "path": "raw/z", "size": 2, "mtime": "later"},
            {"sha256": "a", "path": "raw/a", "size": 1, "mtime": "now"},
            {"sha256": "b", "path": "raw/z", "size": 3, "mtime": "duplicate"},
        ],
        sort=True,
    )

    assert refs == [
        {"sha256": "a", "path": "raw/a", "size": 1, "mtime": "now"},
        {"sha256": "b", "path": "raw/z", "size": 2, "mtime": "later"},
    ]


def test_provenance_tracker_queries_raw_refs_with_shared_extractor(tmp_path: Path) -> None:
    tracker = ProvenanceTracker(tmp_path)
    record_path = tmp_path / "normalized" / "record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    _ = record_path.write_text(
        '{"provenance":{"raw_refs":[{"sha256":"abc","path":"raw/source","size":1,"mtime":"now"}]}}',
        encoding="utf-8",
    )

    assert tracker.query_raw_sources(record_path) == [
        {"sha256": "abc", "path": "raw/source", "size": 1, "mtime": "now"}
    ]
