from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.rglob(pattern))


def run_status(root: Path) -> dict[str, Any]:
    zones = {
        "raw": _count_files(root / "raw", "*"),
        "normalized": _count_files(root / "normalized", "*.json"),
        "compiled": _count_files(root / "compiled", "*.md"),
        "index": _count_files(root / "index", "*.json"),
        "quarantine": _count_files(root / "quarantine", "*"),
    }
    manifest_path = root / "index" / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else None
    )
    return {"root": root.as_posix(), "zones": zones, "index_manifest": manifest}


def _render_status_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    zones = result["zones"]
    return "\n".join(
        [
            f"Snowiki status for {result['root']}",
            f"raw: {zones['raw']}",
            f"normalized: {zones['normalized']}",
            f"compiled: {zones['compiled']}",
            f"index: {zones['index']}",
            f"quarantine: {zones['quarantine']}",
        ]
    )


@click.command("status")
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(output: str) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_status(Path.cwd())
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="status_failed")
    if result is None:
        raise RuntimeError("status did not produce a result")
    emit_result(
        {"ok": True, "command": "status", "result": result},
        output=output_mode,
        human_renderer=_render_status_human,
    )
