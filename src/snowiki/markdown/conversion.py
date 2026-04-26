from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class _MarkItDownConverter(Protocol):
    def convert(self, source: str) -> object:
        """Convert a source path to a MarkItDown result object."""


@dataclass(frozen=True, slots=True)
class ConvertedMarkdownDocument:
    """Markdown text converted from a non-Markdown source document."""

    markdown: str
    title: str | None
    source_path: str


def convert_non_markdown_source(path: str | Path) -> ConvertedMarkdownDocument:
    """Convert a non-Markdown source file into Markdown text with MarkItDown."""
    source_path = Path(path)
    converter = _create_markitdown_converter()
    result = converter.convert(source_path.as_posix())
    markdown = _converted_markdown_text(result)
    title = getattr(result, "title", None)
    return ConvertedMarkdownDocument(
        markdown=markdown,
        title=title if isinstance(title, str) and title.strip() else None,
        source_path=source_path.as_posix(),
    )


def _create_markitdown_converter() -> _MarkItDownConverter:
    from markitdown import MarkItDown

    return MarkItDown(enable_plugins=False)


def _converted_markdown_text(result: object) -> str:
    markdown = getattr(result, "markdown", None)
    if isinstance(markdown, str):
        return markdown
    text_content = getattr(result, "text_content", None)
    if isinstance(text_content, str):
        return text_content
    raise TypeError("MarkItDown conversion result did not include Markdown text")
