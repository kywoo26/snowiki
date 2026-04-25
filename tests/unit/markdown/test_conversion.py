from __future__ import annotations

from pathlib import Path

import pytest

import snowiki.markdown.conversion as conversion_module
from snowiki.markdown.conversion import convert_non_markdown_source


def test_convert_non_markdown_source_uses_markitdown_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "guide.docx"
    _ = source.write_bytes(b"fake docx")
    calls: list[str] = []

    class FakeResult:
        markdown = "# Converted\n\nBody"
        title = "Converted"

    class FakeMarkItDown:
        def __init__(self, *, enable_plugins: bool) -> None:
            calls.append(f"plugins:{enable_plugins}")

        def convert(self, path: str) -> FakeResult:
            calls.append(path)
            return FakeResult()

    monkeypatch.setattr(conversion_module, "MarkItDown", FakeMarkItDown)

    converted = convert_non_markdown_source(source)

    assert converted.markdown == "# Converted\n\nBody"
    assert converted.title == "Converted"
    assert converted.source_path == source.as_posix()
    assert calls == ["plugins:False", source.as_posix()]


def test_convert_non_markdown_source_accepts_legacy_text_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "guide.pdf"

    class FakeResult:
        text_content = "# Converted"
        title = ""

    class FakeMarkItDown:
        def __init__(self, *, enable_plugins: bool) -> None:
            self.enable_plugins = enable_plugins

        def convert(self, path: str) -> FakeResult:
            _ = path
            return FakeResult()

    monkeypatch.setattr(conversion_module, "MarkItDown", FakeMarkItDown)

    converted = convert_non_markdown_source(source)

    assert converted.markdown == "# Converted"
    assert converted.title is None
