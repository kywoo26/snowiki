from __future__ import annotations

from pathlib import Path

from snowiki.lint.stale_links import find_stale_wikilinks


def test_find_stale_wikilinks_reports_missing_targets(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled"
    compiled.mkdir(parents=True)
    (compiled / "overview.md").write_text(
        "# Overview\n\n[[compiled/topics/live]]\n[[compiled/topics/missing|Missing]]\n",
        encoding="utf-8",
    )
    topics = compiled / "topics"
    topics.mkdir()
    (topics / "live.md").write_text("# Live\n", encoding="utf-8")

    issues = find_stale_wikilinks(tmp_path)

    assert issues == [
        {
            "code": "L002",
            "severity": "error",
            "path": "compiled/overview.md",
            "message": "broken wikilink: [[compiled/topics/missing]]",
            "target": "compiled/topics/missing.md",
        }
    ]
