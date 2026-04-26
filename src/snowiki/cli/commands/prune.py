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
from snowiki.cli.decorators import destructive_options, output_option, root_option
from snowiki.cli.output import (
    emit_command_result,
    emit_error,
    validate_destructive_flags,
)
from snowiki.markdown.source_prune import prune_missing_markdown_sources


def _render_sources_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    action = "Would delete" if result["dry_run"] else "Deleted"
    lines = [
        f"{action} {result['candidate_count']} source prune candidate(s) in {result['root']}",
        f"deleted: {result['deleted_count']}",
    ]
    for candidate in result["candidates"]:
        lines.append(f"- {candidate['kind']}: {candidate['path']}")
    tombstone_path = result.get("tombstone_path")
    if tombstone_path:
        lines.append(f"tombstone: {tombstone_path}")
    return "\n".join(lines)


@click.group(
    "prune",
    no_args_is_help=True,
    short_help="Dry-run-first cleanup commands.",
)
def command() -> None:
    """Dry-run-first cleanup commands for stale Snowiki artifacts."""


@command.command("sources", short_help="Prune missing Markdown source records.")
@click.option(
    "--all-candidates",
    is_flag=True,
    help="Confirm that all reported source prune candidates may be deleted.",
)
@destructive_options
@root_option
@output_option
@pass_snowiki_context
def sources_command(
    cli_context: SnowikiCliContext,
    all_candidates: bool,
    dry_run: bool,
    delete_artifacts: bool,
    yes: bool,
    root: Path | None,
    output: str,
) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    validate_destructive_flags(
        dry_run=dry_run,
        delete_artifacts=delete_artifacts,
        yes=yes,
        output=output_mode,
        code="prune_confirmation_required",
        conflict_code="prune_failed",
        confirmation_message="source prune deletion requires --yes",
    )
    if delete_artifacts and not all_candidates:
        emit_error(
            "source prune deletion requires --all-candidates",
            output=output_mode,
            code="prune_confirmation_required",
        )
    try:
        result = prune_missing_markdown_sources(
            initialize_cli_root(cli_context),
            dry_run=not delete_artifacts,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="prune_failed")
    emit_command_result(
        result,
        command="prune sources",
        output=output_mode,
        human_renderer=_render_sources_human,
    )
