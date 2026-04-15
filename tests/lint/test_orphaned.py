from __future__ import annotations

from pathlib import Path

from snowiki.lint.orphaned import find_orphaned_compiled_pages


def test_find_orphaned_compiled_pages_returns_pages_without_inbound_links(
    tmp_path: Path,
) -> None:
    compiled = tmp_path / "compiled"
    compiled.mkdir(parents=True)
    (compiled / "overview.md").write_text(
        "# Overview\n\n[[compiled/topics/linked]]\n", encoding="utf-8"
    )
    topics = compiled / "topics"
    topics.mkdir()
    (topics / "linked.md").write_text("# Linked\n", encoding="utf-8")
    (topics / "orphaned.md").write_text("# Orphaned\n", encoding="utf-8")

    issues = find_orphaned_compiled_pages(tmp_path)

    assert issues == [
        {
            "code": "L301",
            "check": "graph.orphan_compiled_page",
            "severity": "warning",
            "path": "compiled/topics/orphaned.md",
            "message": "compiled page has no inbound wikilinks",
        }
    ]
