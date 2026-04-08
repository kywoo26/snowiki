from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def run_export(root: Path, export_format: str) -> dict[str, Any]:
    if export_format == "json":
        records = []
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

    pages = []
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


def _render_export_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    key = "records" if result["format"] == "json" else "pages"
    return f"Exported {len(result[key])} item(s) as {result['format']}"


@click.command("export")
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    required=True,
)
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(export_format: str, output: str) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_export(Path.cwd(), export_format)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="export_failed")
    if result is None:
        raise RuntimeError("export did not produce a result")
    emit_result(
        {"ok": True, "command": "export", "result": result},
        output=output_mode,
        human_renderer=_render_export_human,
    )
