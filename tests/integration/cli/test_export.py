from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from snowiki.cli.main import app


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_export_json_outputs_normalized_records(tmp_path: Path) -> None:
    runner = CliRunner()
    _write_json(
        tmp_path / "normalized" / "markdown" / "record-a.json",
        {"id": "record-a", "record_type": "markdown_document"},
    )

    result = runner.invoke(
        app,
        ["export", "--format", "json", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "export",
        "result": {
            "format": "json",
            "records": [
                {
                    "path": "normalized/markdown/record-a.json",
                    "record": {"id": "record-a", "record_type": "markdown_document"},
                }
            ],
        },
    }


def test_export_markdown_outputs_compiled_pages(tmp_path: Path) -> None:
    runner = CliRunner()
    _write_text(tmp_path / "compiled" / "overview.md", "# Overview\n")

    result = runner.invoke(
        app,
        ["export", "--format", "markdown", "--output", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "export",
        "result": {
            "format": "markdown",
            "pages": [{"path": "compiled/overview.md", "content": "# Overview\n"}],
        },
    }


def test_export_human_reports_empty_workspace(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["export", "--format", "json"],
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert result.output == "Exported 0 item(s) as json\n"
