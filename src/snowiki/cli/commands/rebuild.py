from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.context import (
    SnowikiCliContext,
    bind_cli_context,
    initialize_cli_root,
    pass_snowiki_context,
)
from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result
from snowiki.rebuild.integrity import RebuildFreshnessError, run_rebuild_with_integrity


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


@click.command("rebuild", short_help="Rebuild compiled artifacts and search index.")
@output_option
@root_option
@pass_snowiki_context
def command(cli_context: SnowikiCliContext, output: str, root: Path | None) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    result: dict[str, Any] | None = None
    try:
        result = run_rebuild(initialize_cli_root(cli_context))
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
        raise click.ClickException("rebuild did not produce a result")
    emit_result(
        {"ok": True, "command": "rebuild", "result": result},
        output=output_mode,
        human_renderer=_render_rebuild_human,
    )
