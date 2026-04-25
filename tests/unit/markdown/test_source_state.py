from __future__ import annotations

import json
from pathlib import Path

from snowiki.markdown.ingest import run_markdown_ingest
from snowiki.markdown.source_state import (
    collect_markdown_source_state,
    count_stale_markdown_sources,
    plan_missing_source_prune,
)


def test_collect_markdown_source_state_reports_all_states(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    current = source_root / "current.md"
    modified = source_root / "modified.md"
    missing = source_root / "missing.md"
    untracked = source_root / "untracked.md"
    _ = current.write_text("# Current\n", encoding="utf-8")
    _ = modified.write_text("# Modified\n", encoding="utf-8")
    _ = missing.write_text("# Missing\n", encoding="utf-8")
    storage_root = tmp_path / "snowiki"

    result = run_markdown_ingest(source_root, root=storage_root)
    assert result["documents_stale"] == 0
    _ = modified.write_text("# Modified\n\nChanged.\n", encoding="utf-8")
    missing.unlink()
    _ = untracked.write_text("# Untracked\n", encoding="utf-8")

    report = collect_markdown_source_state(storage_root)

    assert report["counts"] == {
        "invalid": 0,
        "modified": 1,
        "missing": 1,
        "untracked": 1,
        "current": 1,
    }
    assert report["stale_count"] == 3
    assert {item["relative_path"]: item["state"] for item in report["items"]} == {
        "modified.md": "modified",
        "missing.md": "missing",
        "untracked.md": "untracked",
        "current.md": "current",
    }
    modified_item = next(item for item in report["items"] if item["relative_path"] == "modified.md")
    assert modified_item["stored_content_hash"] != modified_item["current_content_hash"]
    assert modified_item.get("normalized_path", "").startswith("normalized/markdown/documents/")
    untracked_item = next(item for item in report["items"] if item["relative_path"] == "untracked.md")
    assert "normalized_path" not in untracked_item


def test_source_state_counts_and_prune_plan_share_markdown_records(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first_note = first_root / "note.md"
    second_note = second_root / "note.md"
    _ = first_note.write_text("# First\n", encoding="utf-8")
    _ = second_note.write_text("# Second\n", encoding="utf-8")
    storage_root = tmp_path / "snowiki"
    _ = run_markdown_ingest(first_root, root=storage_root)
    _ = run_markdown_ingest(second_root, root=storage_root)

    first_note.unlink()
    _ = (second_root / "extra.md").write_text("# Extra\n", encoding="utf-8")

    assert count_stale_markdown_sources(storage_root) == 2
    assert count_stale_markdown_sources(storage_root, source_root=first_root) == 1
    assert count_stale_markdown_sources(storage_root, source_root=second_root) == 1
    assert (
        count_stale_markdown_sources(
            storage_root, source_root=second_root, include_untracked=False
        )
        == 0
    )
    candidates = plan_missing_source_prune(storage_root)
    assert [candidate["kind"] for candidate in candidates] == [
        "normalized_markdown_record",
        "raw_snapshot",
    ]


def test_source_state_reports_out_of_root_metadata_without_hashing(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    outside = tmp_path / "outside.md"
    _ = outside.write_text("# Outside\n", encoding="utf-8")
    record_path = tmp_path / "snowiki" / "normalized" / "markdown" / "documents" / "bad.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json_payload(
            {
                "id": "bad",
                "source_type": "markdown",
                "record_type": "document",
                "source_root": source_root.as_posix(),
                "relative_path": "../outside.md",
                "source_path": outside.as_posix(),
                "content_hash": "not-used",
            }
        ),
        encoding="utf-8",
    )

    report = collect_markdown_source_state(tmp_path / "snowiki")

    assert report["counts"]["invalid"] == 1
    item = report["items"][0]
    assert item["state"] == "invalid"
    assert item.get("error") == "relative_path must stay inside source_root"


def test_prune_plan_rejects_traversing_raw_refs(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    missing = source_root / "missing.md"
    snowiki_root = tmp_path / "snowiki"
    record_path = snowiki_root / "normalized" / "markdown" / "documents" / "missing.json"
    record_path.parent.mkdir(parents=True)
    (snowiki_root / "index").mkdir(parents=True)
    (snowiki_root / "index" / "manifest.json").write_text("{}", encoding="utf-8")
    record_path.write_text(
        json_payload(
            {
                "id": "missing",
                "source_type": "markdown",
                "record_type": "document",
                "source_root": source_root.as_posix(),
                "relative_path": "missing.md",
                "source_path": missing.as_posix(),
                "content_hash": "abc",
                "raw_refs": [{"path": "raw/../index/manifest.json"}],
            }
        ),
        encoding="utf-8",
    )

    candidates = plan_missing_source_prune(snowiki_root)

    assert candidates == [
        {
            "kind": "normalized_markdown_record",
            "path": "normalized/markdown/documents/missing.json",
            "reason": "source_missing",
            "record_id": "missing",
            "source_path": missing.as_posix(),
        }
    ]


def test_missing_record_does_not_trigger_untracked_scan_of_broad_root(tmp_path: Path) -> None:
    broad_root = tmp_path / "broad"
    broad_root.mkdir()
    _ = (broad_root / "untracked.md").write_text("# Should Not Scan\n", encoding="utf-8")
    missing = broad_root / "missing.md"
    snowiki_root = tmp_path / "snowiki"
    record_path = snowiki_root / "normalized" / "markdown" / "documents" / "missing.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json_payload(
            {
                "id": "missing",
                "source_type": "markdown",
                "record_type": "document",
                "source_root": broad_root.as_posix(),
                "relative_path": "missing.md",
                "source_path": missing.as_posix(),
                "content_hash": "abc",
            }
        ),
        encoding="utf-8",
    )

    report = collect_markdown_source_state(snowiki_root)

    assert {item["relative_path"]: item["state"] for item in report["items"]} == {
        "missing.md": "missing"
    }


def json_payload(payload: object) -> str:
    return json.dumps(payload)
