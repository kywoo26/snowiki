from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
SKIP_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".sisyphus",
        ".svn",
        ".tox",
        ".venv",
        "compiled",
        "index",
        "node_modules",
        "normalized",
        "queue",
        "raw",
    }
)


@dataclass(frozen=True, slots=True)
class MarkdownSource:
    path: Path
    source_root: Path
    relative_path: str


def discover_markdown_sources(path: Path, *, source_root: Path | None = None) -> list[MarkdownSource]:
    """Discover Markdown files without following symlinks or internal directories."""
    expanded_path = path.expanduser()
    if expanded_path.is_symlink():
        return []
    if not expanded_path.exists():
        raise ValueError(f"path does not exist: {path}")
    resolved_path = expanded_path.resolve(strict=True)
    resolved_root = _resolve_source_root(resolved_path, source_root=source_root)

    if resolved_path.is_file():
        if not _is_markdown_file(resolved_path):
            raise ValueError(f"expected a Markdown file, got {resolved_path}")
        return [_source_for_path(resolved_path, source_root=resolved_root)]

    if not resolved_path.is_dir():
        raise ValueError(f"expected a Markdown file or directory, got {resolved_path}")

    sources: list[MarkdownSource] = []
    for child in sorted(resolved_path.iterdir(), key=lambda candidate: candidate.as_posix()):
        if child.is_symlink():
            continue
        if child.is_dir():
            if _should_skip_directory(child):
                continue
            sources.extend(_discover_directory(child, source_root=resolved_root))
            continue
        if _is_markdown_file(child):
            sources.append(_source_for_path(child, source_root=resolved_root))
    return sources


def _discover_directory(path: Path, *, source_root: Path) -> list[MarkdownSource]:
    sources: list[MarkdownSource] = []
    for child in sorted(path.iterdir(), key=lambda candidate: candidate.as_posix()):
        if child.is_symlink():
            continue
        if child.is_dir():
            if _should_skip_directory(child):
                continue
            sources.extend(_discover_directory(child, source_root=source_root))
            continue
        if _is_markdown_file(child):
            sources.append(_source_for_path(child, source_root=source_root))
    return sources


def _resolve_source_root(path: Path, *, source_root: Path | None) -> Path:
    if source_root is None:
        return path if path.is_dir() else path.parent
    resolved_root = source_root.expanduser().resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError(f"source_root must be a directory: {source_root}")
    try:
        _ = path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path must be inside source_root: {path}") from exc
    return resolved_root


def _source_for_path(path: Path, *, source_root: Path) -> MarkdownSource:
    return MarkdownSource(
        path=path,
        source_root=source_root,
        relative_path=path.relative_to(source_root).as_posix(),
    )


def _is_markdown_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES


def _should_skip_directory(path: Path) -> bool:
    return path.name.startswith(".") or path.name in SKIP_DIRECTORY_NAMES
