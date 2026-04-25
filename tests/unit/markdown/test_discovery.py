from __future__ import annotations

from pathlib import Path

import pytest

from snowiki.markdown import discover_markdown_sources


def test_discover_markdown_sources_recurses_and_skips_internal_dirs(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    nested = docs / "nested"
    raw = docs / "raw"
    hidden = docs / ".sisyphus"
    nested.mkdir(parents=True)
    raw.mkdir()
    hidden.mkdir()
    _ = (docs / "README.md").write_text("# Readme", encoding="utf-8")
    _ = (nested / "note.markdown").write_text("# Note", encoding="utf-8")
    _ = (docs / "ignore.txt").write_text("ignore", encoding="utf-8")
    _ = (raw / "internal.md").write_text("# Internal", encoding="utf-8")
    _ = (hidden / "hidden.md").write_text("# Hidden", encoding="utf-8")

    sources = discover_markdown_sources(docs)

    assert [source.relative_path for source in sources] == [
        "README.md",
        "nested/note.markdown",
    ]
    assert {source.source_root for source in sources} == {docs.resolve()}


def test_discover_markdown_sources_uses_parent_as_file_default_root(
    tmp_path: Path,
) -> None:
    note = tmp_path / "note.md"
    _ = note.write_text("# Note", encoding="utf-8")

    sources = discover_markdown_sources(note)

    assert len(sources) == 1
    assert sources[0].source_root == tmp_path.resolve()
    assert sources[0].relative_path == "note.md"


def test_discover_markdown_sources_requires_path_inside_source_root(
    tmp_path: Path,
) -> None:
    note = tmp_path / "note.md"
    other_root = tmp_path / "other"
    _ = note.write_text("# Note", encoding="utf-8")
    other_root.mkdir()

    with pytest.raises(ValueError, match="path must be inside source_root"):
        _ = discover_markdown_sources(note, source_root=other_root)


def test_discover_markdown_sources_skips_explicit_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.md"
    link = tmp_path / "linked.md"
    _ = target.write_text("# Target", encoding="utf-8")
    link.symlink_to(target)

    assert discover_markdown_sources(link) == []
