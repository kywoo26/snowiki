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
from snowiki.storage.export_bundle import build_export_bundle


def _render_export_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    key = "records" if result["format"] == "json" else "pages"
    return f"Exported {len(result[key])} item(s) as {result['format']}"


@click.command("export", short_help="Export compiled wiki data.")
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    required=True,
)
@output_option
@root_option
@pass_snowiki_context
def command(
    cli_context: SnowikiCliContext, export_format: str, output: str, root: Path | None
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = build_export_bundle(initialize_cli_root(cli_context), export_format)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="export_failed")
    emit_result(
        {"ok": True, "command": "export", "result": result},
        output=output_mode,
        human_renderer=_render_export_human,
    )
