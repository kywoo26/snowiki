from __future__ import annotations

from snowiki.schema.compiled import CompiledPage

from .taxonomy import sorted_unique


def wikilink(path: str) -> str:
    target = path[:-3] if path.endswith(".md") else path
    return f"[[{target}]]"


def apply_backlinks(pages: list[CompiledPage]) -> list[CompiledPage]:
    pages_by_path = {page.path: page for page in pages}
    for page in pages:
        page.related = sorted_unique(
            related_path for related_path in page.related if related_path != page.path
        )

    for page in pages:
        for related_path in list(page.related):
            related_page = pages_by_path.get(related_path)
            if related_page is None or related_page.path == page.path:
                continue
            related_page.related = sorted_unique([*related_page.related, page.path])

    return sorted(pages, key=lambda page: page.path)


def render_related_section(paths: list[str]) -> str:
    related_paths = sorted_unique(paths)
    if not related_paths:
        return "## Related\n\n- _None yet._"
    lines = ["## Related", ""]
    for path in related_paths:
        lines.append(f"- {wikilink(path)}")
    return "\n".join(lines)
