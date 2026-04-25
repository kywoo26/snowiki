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
from snowiki.search.queries import run_recall


def _render_recall_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [f"Recall strategy: {result['strategy']}", f"hits: {len(result['hits'])}"]
    for index, hit in enumerate(result["hits"], start=1):
        lines.append(f"{index}. [{hit['kind']}] {hit['title']} ({hit['path']})")
    return "\n".join(lines)


@click.command("recall", short_help="Recall by temporal or topical target.")
@click.argument("target")
@output_option
@root_option
@pass_snowiki_context
def command(
    cli_context: SnowikiCliContext, target: str, output: str, root: Path | None
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = run_recall(initialize_cli_root(cli_context), target)
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="recall_failed")
    emit_result(
        {"ok": True, "command": "recall", "result": result},
        output=output_mode,
        human_renderer=_render_recall_human,
    )
