from __future__ import annotations

import json
from pathlib import Path

from snowiki.markdown.ingest import run_markdown_ingest
from snowiki.markdown.source_prune import (
    SourcePruneCandidate,
    _write_tombstone,
    plan_missing_source_prune,
)
from snowiki.markdown.source_state import count_stale_markdown_sources


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


def test_prune_plan_ignores_malformed_raw_refs_and_missing_raw_files(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    missing = source_root / "missing.md"
    snowiki_root = tmp_path / "snowiki"
    record_path = snowiki_root / "normalized" / "markdown" / "documents" / "missing.json"
    record_path.parent.mkdir(parents=True)
    (snowiki_root / "index").mkdir(parents=True)
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
                "raw_refs": ["raw/not-a-dict.json", {}, {"path": "raw/missing.json"}],
            }
        ),
        encoding="utf-8",
    )

    candidates = plan_missing_source_prune(snowiki_root)

    assert [candidate["kind"] for candidate in candidates] == ["normalized_markdown_record"]


def test_source_prune_tombstone_appends_existing_entries(tmp_path: Path) -> None:
    snowiki_root = tmp_path / "snowiki"
    tombstone_path = snowiki_root / "index" / "source-prune-tombstones.json"
    tombstone_path.parent.mkdir(parents=True)
    tombstone_path.write_text(json_payload([{"existing": True}, "skip-me"]), encoding="utf-8")
    candidates: list[SourcePruneCandidate] = [
        {
            "kind": "normalized_markdown_record",
            "path": "normalized/markdown/documents/missing.json",
            "reason": "source_missing",
            "record_id": "missing",
            "source_path": "/tmp/missing.md",
        }
    ]

    written_path = _write_tombstone(snowiki_root, candidates, [candidates[0]["path"]])
    payload = json.loads(written_path.read_text(encoding="utf-8"))

    assert payload[0] == {"existing": True}
    assert payload[1]["candidates"] == candidates
    assert payload[1]["deleted"] == ["normalized/markdown/documents/missing.json"]


def json_payload(payload: object) -> str:
    return json.dumps(payload)
