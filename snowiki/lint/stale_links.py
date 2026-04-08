from __future__ import annotations

import re
from pathlib import Path

_WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _normalize_target(target: str) -> str:
    cleaned = target.strip().split("|", 1)[0].split("#", 1)[0].strip()
    if not cleaned:
        return ""
    if not cleaned.endswith(".md"):
        cleaned = f"{cleaned}.md"
    return Path(cleaned).as_posix()


def extract_wikilinks(text: str) -> list[str]:
    links: list[str] = []
    for match in _WIKILINK_PATTERN.finditer(text):
        target = _normalize_target(match.group(1))
        if target:
            links.append(target)
    return links


def find_stale_wikilinks(root: str | Path) -> list[dict[str, str]]:
    base = Path(root)
    issues: list[dict[str, str]] = []
    for path in sorted(
        (base / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    ):
        text = path.read_text(encoding="utf-8")
        for target in extract_wikilinks(text):
            resolved = base / target
            if resolved.exists():
                continue
            issues.append(
                {
                    "code": "L002",
                    "severity": "error",
                    "path": path.relative_to(base).as_posix(),
                    "message": f"broken wikilink: [[{target[:-3]}]]",
                    "target": target,
                }
            )
    return issues
