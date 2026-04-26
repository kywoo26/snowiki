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
from snowiki.status import run_status


def _render_mapping_line(label: str, values: dict[str, int]) -> str:
    rendered = ", ".join(f"{key}: {values[key]}" for key in values)
    return f"{label}: {rendered}" if rendered else f"{label}: none"


def _render_status_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    pages = result["pages"]
    sources = result["sources"]
    lint = result["lint"]
    freshness = result["freshness"]
    source_freshness = sources["freshness"]
    manifest = result["manifest"]
    summary = lint["summary"]

    current_tokenizer = freshness["current_content_identity"].get("tokenizer", {})
    tokenizer_name = current_tokenizer.get("name", "n/a")

    freshness_bits = [
        f"state={freshness['status']}",
        f"tokenizer={tokenizer_name}",
        f"latest normalized={freshness['latest_normalized_recorded_at'] or 'n/a'}",
        f"latest compiled={freshness['latest_compiled_update'] or 'n/a'}",
    ]
    source_freshness_bits = [
        f"stale={source_freshness['stale_count']}",
        *[
            f"{state}={count}"
            for state, count in source_freshness["counts"].items()
        ],
    ]
    manifest_bits = [
        f"tokenizer={manifest['tokenizer_name'] or 'n/a'}",
        f"records indexed={manifest['records_indexed'] if manifest['records_indexed'] is not None else 'n/a'}",
        f"pages indexed={manifest['pages_indexed'] if manifest['pages_indexed'] is not None else 'n/a'}",
        f"search documents={manifest['search_documents'] if manifest['search_documents'] is not None else 'n/a'}",
        f"compiled paths={manifest['compiled_path_count'] if manifest['compiled_path_count'] is not None else 'n/a'}",
    ]

    lines = [
        f"Snowiki status for {result['root']}",
        f"Pages: {pages['total']} total",
        _render_mapping_line("  By type", pages["by_type"]),
        f"Sources: {sources['total']} total",
        _render_mapping_line("  By source", sources["by_type"]),
        (
            "Lint: "
            f"{summary['error']} errors, {summary['warning']} warnings, {summary['info']} info"
        ),
        f"Freshness: {', '.join(freshness_bits)}",
        f"Source Freshness: {', '.join(source_freshness_bits)}",
        f"Manifest: {', '.join(manifest_bits)}",
    ]

    return "\n".join(lines)


@click.command("status", short_help="Summarize wiki health and freshness.")
@root_option
@output_option
@pass_snowiki_context
def command(cli_context: SnowikiCliContext, root: Path | None, output: str) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = run_status(initialize_cli_root(cli_context))
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="status_failed")
    emit_command_result(
        result,
        command="status",
        output=output_mode,
        human_renderer=_render_status_human,
    )
