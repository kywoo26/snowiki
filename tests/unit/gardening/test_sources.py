from __future__ import annotations

from pathlib import Path

from snowiki.gardening.sources import collect_source_gardening_proposals
from snowiki.markdown.ingest import run_markdown_ingest


def test_source_gardening_reports_exact_hash_rename_candidate(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    anchor = source_root / "anchor.md"
    old = source_root / "old-name.md"
    new = source_root / "new-name.md"
    _ = anchor.write_text("# Anchor\n", encoding="utf-8")
    _ = old.write_text("# Topic\n\nSame content.\n", encoding="utf-8")
    storage_root = tmp_path / "snowiki"
    _ = run_markdown_ingest(source_root, root=storage_root)
    old.unlink()
    _ = new.write_text("# Topic\n\nSame content.\n", encoding="utf-8")

    report = collect_source_gardening_proposals(storage_root)

    assert report["dry_run"] is True
    rename = next(
        proposal
        for proposal in report["proposals"]
        if proposal["proposal_type"] == "source_rename_candidate"
    )
    assert rename["risk"] == "low"
    assert rename["apply_supported"] is False
    assert rename["recommended_action"] == "reingest_new_source_then_review_prune_old_record"
    assert [evidence["relative_path"] for evidence in rename["evidence"]] == [
        "old-name.md",
        "new-name.md",
    ]

    assert collect_source_gardening_proposals(storage_root) == report


def test_source_gardening_reports_manual_when_rename_is_ambiguous(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    anchor = source_root / "anchor.md"
    old = source_root / "old-name.md"
    first = source_root / "first-copy.md"
    second = source_root / "second-copy.md"
    content = "# Topic\n\nSame content.\n"
    _ = anchor.write_text("# Anchor\n", encoding="utf-8")
    _ = old.write_text(content, encoding="utf-8")
    storage_root = tmp_path / "snowiki"
    _ = run_markdown_ingest(source_root, root=storage_root)
    old.unlink()
    _ = first.write_text(content, encoding="utf-8")
    _ = second.write_text(content, encoding="utf-8")

    report = collect_source_gardening_proposals(storage_root)

    assert not any(
        proposal["proposal_type"] == "source_rename_candidate"
        for proposal in report["proposals"]
    )
    missing_manual = next(
        proposal
        for proposal in report["proposals"]
        if proposal["recommended_action"] == "review_missing_source_for_prune_or_rename"
    )
    assert missing_manual["proposal_type"] == "manual_gardening_required"
    assert missing_manual["manual_reason"] == (
        "missing source did not have exactly one same-hash untracked rename candidate"
    )


def test_source_gardening_reports_manual_for_many_to_one_rename(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    anchor = source_root / "anchor.md"
    first_old = source_root / "first-old.md"
    second_old = source_root / "second-old.md"
    new = source_root / "new-name.md"
    content = "# Topic\n\nSame content.\n"
    _ = anchor.write_text("# Anchor\n", encoding="utf-8")
    _ = first_old.write_text(content, encoding="utf-8")
    _ = second_old.write_text(content, encoding="utf-8")
    storage_root = tmp_path / "snowiki"
    _ = run_markdown_ingest(source_root, root=storage_root)
    first_old.unlink()
    second_old.unlink()
    _ = new.write_text(content, encoding="utf-8")

    report = collect_source_gardening_proposals(storage_root)

    assert not any(
        proposal["proposal_type"] == "source_rename_candidate"
        for proposal in report["proposals"]
    )
    missing_manuals = [
        proposal
        for proposal in report["proposals"]
        if proposal["recommended_action"] == "review_missing_source_for_prune_or_rename"
    ]
    assert len(missing_manuals) == 2


def test_source_gardening_ignores_current_sources(tmp_path: Path) -> None:
    source_root = tmp_path / "vault"
    source_root.mkdir()
    note = source_root / "note.md"
    _ = note.write_text("# Note\n", encoding="utf-8")
    storage_root = tmp_path / "snowiki"
    _ = run_markdown_ingest(source_root, root=storage_root)

    report = collect_source_gardening_proposals(storage_root)

    assert report["proposal_count"] == 0
    assert report["proposals"] == []
