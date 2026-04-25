from __future__ import annotations

import json
from pathlib import Path

from snowiki.storage.export_bundle import build_export_bundle


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_json_export_bundle_reads_normalized_records(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "normalized" / "markdown" / "record-a.json",
        {"id": "record-a", "record_type": "markdown_document"},
    )

    assert build_export_bundle(tmp_path, "json") == {
        "format": "json",
        "records": [
            {
                "path": "normalized/markdown/record-a.json",
                "record": {"id": "record-a", "record_type": "markdown_document"},
            }
        ],
    }


def test_build_markdown_export_bundle_reads_compiled_pages(tmp_path: Path) -> None:
    _write_text(tmp_path / "compiled" / "overview.md", "# Overview\n")

    assert build_export_bundle(tmp_path, "markdown") == {
        "format": "markdown",
        "pages": [{"path": "compiled/overview.md", "content": "# Overview\n"}],
    }
