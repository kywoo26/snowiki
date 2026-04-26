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
from snowiki.cli.output import emit_command_result, emit_error
from snowiki.markdown.ingest import run_markdown_ingest


def _render_ingest_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    lines = [
        f"Ingested Markdown sources into {result['root']}",
        f"source_root: {result['source_root']}",
        f"documents_seen: {result['documents_seen']}",
        f"documents_inserted: {result['documents_inserted']}",
        f"documents_updated: {result['documents_updated']}",
        f"documents_unchanged: {result['documents_unchanged']}",
        f"documents_stale: {result['documents_stale']}",
        f"rebuild_required: {result['rebuild_required']}",
    ]
    rebuild = result.get("rebuild")
    if isinstance(rebuild, dict):
        lines.append(f"compiled_paths: {rebuild.get('compiled_count', 0)}")
    return "\n".join(lines)


def _error_code_for_value_error(message: str) -> str:
    return "privacy_blocked" if message.startswith("sensitive path excluded") else "ingest_failed"


@click.command("ingest", short_help="Ingest Markdown sources.")
@click.argument("path", type=click.Path(exists=False, path_type=Path))
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Canonical source root for Markdown identity.",
)
@click.option("--rebuild", is_flag=True, help="Rebuild compiled artifacts after ingest.")
@root_option
@output_option
@pass_snowiki_context
def command(
    cli_context: SnowikiCliContext,
    path: Path,
    source_root: Path | None,
    rebuild: bool,
    root: Path | None,
    output: str,
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        storage_root = initialize_cli_root(cli_context)
        result = run_markdown_ingest(
            path,
            root=storage_root,
            source_root=source_root,
            rebuild=rebuild,
        )
    except click.ClickException as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="ingest_failed",
            details={"path": path.as_posix()},
        )
    except ValueError as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code=_error_code_for_value_error(str(exc)),
            details={"path": path.as_posix()},
        )
    except Exception as exc:
        emit_error(
            str(exc),
            output=output_mode,
            code="unexpected_error",
            details={"path": path.as_posix()},
        )

    emit_command_result(
        result,
        command="ingest",
        output=output_mode,
        human_renderer=_render_ingest_human,
    )
