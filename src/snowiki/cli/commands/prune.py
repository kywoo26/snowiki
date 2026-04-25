from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result, normalize_output_mode
from snowiki.config import get_snowiki_root
from snowiki.markdown.source_state import prune_missing_markdown_sources


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


@click.group("prune")
def command() -> None:
    """Dry-run-first cleanup commands for stale Snowiki artifacts."""


@command.command("sources")
@root_option
@output_option
@click.option("--dry-run", is_flag=True, help="Preview source prune candidates.")
@click.option("--delete", "delete_artifacts", is_flag=True, help="Delete candidates.")
@click.option("--yes", is_flag=True, help="Confirm deletion with --delete.")
@click.option(
    "--all-candidates",
    is_flag=True,
    help="Confirm that all reported source prune candidates may be deleted.",
)
def sources_command(
    root: Path | None,
    output: str,
    dry_run: bool,
    delete_artifacts: bool,
    yes: bool,
    all_candidates: bool,
) -> None:
    output_mode = normalize_output_mode(output)
    if dry_run and delete_artifacts:
        emit_error(
            "--dry-run cannot be combined with --delete",
            output=output_mode,
            code="prune_failed",
        )
    if delete_artifacts and not yes:
        emit_error(
            "source prune deletion requires --yes",
            output=output_mode,
            code="prune_confirmation_required",
        )
    if delete_artifacts and not all_candidates:
        emit_error(
            "source prune deletion requires --all-candidates",
            output=output_mode,
            code="prune_confirmation_required",
        )
    try:
        result = prune_missing_markdown_sources(
            root if root is not None else get_snowiki_root(),
            dry_run=not delete_artifacts,
        )
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="prune_failed")
    emit_result(
        {"ok": True, "command": "prune sources", "result": result},
        output=output_mode,
        human_renderer=_render_sources_human,
    )
