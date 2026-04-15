from __future__ import annotations

from pathlib import Path

from .stale_links import extract_wikilinks


def find_orphaned_compiled_pages(root: str | Path) -> list[dict[str, str]]:
    base = Path(root)
    compiled_paths = sorted(
        (base / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    )
    inbound_counts = {path.relative_to(base).as_posix(): 0 for path in compiled_paths}

    for path in compiled_paths:
        current = path.relative_to(base).as_posix()
        text = path.read_text(encoding="utf-8")
        for target in set(extract_wikilinks(text)):
            if target == current:
                continue
            if target in inbound_counts:
                inbound_counts[target] += 1

    issues: list[dict[str, str]] = []
    for relative_path, inbound_count in sorted(inbound_counts.items()):
        if relative_path == "compiled/overview.md" or inbound_count > 0:
            continue
        issues.append(
            {
                "code": "L301",
                "check": "graph.orphan_compiled_page",
                "severity": "warning",
                "path": relative_path,
                "message": "compiled page has no inbound wikilinks",
            }
        )
    return issues
