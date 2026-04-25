from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, TypedDict

ExportFormat = Literal["json", "markdown"]


class ExportRecord(TypedDict):
    path: str
    record: Any


class ExportPage(TypedDict):
    path: str
    content: str


class JsonExportResult(TypedDict):
    format: Literal["json"]
    records: list[ExportRecord]


class MarkdownExportResult(TypedDict):
    format: Literal["markdown"]
    pages: list[ExportPage]


ExportResult = JsonExportResult | MarkdownExportResult


def build_export_bundle(root: Path, export_format: str) -> ExportResult:
    """Build a portable export bundle from Snowiki storage artifacts."""
    if export_format == "json":
        records: list[ExportRecord] = []
        for path in sorted(
            (root / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
        ):
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "record": json.loads(path.read_text(encoding="utf-8")),
                }
            )
        return {"format": "json", "records": records}

    pages: list[ExportPage] = []
    for path in sorted(
        (root / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    ):
        pages.append(
            {
                "path": path.relative_to(root).as_posix(),
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return {"format": "markdown", "pages": pages}
