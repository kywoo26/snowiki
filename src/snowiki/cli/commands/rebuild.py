from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result
from snowiki.config import get_snowiki_root
from snowiki.rebuild.integrity import RebuildFreshnessError, run_rebuild_with_integrity


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def _render_rebuild_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Rebuilt compiled wiki in {result['root']}",
        f"compiled_paths: {result['compiled_count']}",
        f"index_manifest: {result['index_manifest']}",
    ]
    if result["compiled_paths"]:
        lines.extend(f"- {path}" for path in result["compiled_paths"])
    return "\n".join(lines)


def run_rebuild(root: Path) -> dict[str, Any]:
    result = run_rebuild_with_integrity(root)
    return {"root": root.as_posix(), **result}


@click.command("rebuild")
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
def command(output: str, root: Path | None) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_rebuild(root if root else get_snowiki_root())
    except RebuildFreshnessError as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="rebuild_failed",
            details=exc.result,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="rebuild_failed")
    if result is None:
        raise RuntimeError("rebuild did not produce a result")
    emit_result(
        {"ok": True, "command": "rebuild", "result": result},
        output=output_mode,
        human_renderer=_render_rebuild_human,
    )
