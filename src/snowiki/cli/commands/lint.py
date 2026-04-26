from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from snowiki.cli.context import (
    SnowikiCliContext,
    bind_cli_context,
    initialize_cli_root,
    pass_snowiki_context,
)
from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_command_result, emit_error, emit_result
from snowiki.lint import LintResult, run_lint


def _render_lint_human(payload: dict[str, object]) -> str:
    result = cast(LintResult, payload["result"])
    summary = result["summary"]
    if not result["issues"]:
        return (
            f"Snowiki lint is healthy for {result['root']}\n"
            f"Summary: 0 errors, 0 warnings, 0 info"
        )

    lines = [
        f"Snowiki lint found {summary['total']} issue(s) in {result['root']}",
        f"Summary: {summary['error']} errors, {summary['warning']} warnings, {summary['info']} info",
    ]
    grouped_labels = [
        ("error", "Errors"),
        ("warning", "Warnings"),
        ("info", "Info"),
    ]
    for severity, label in grouped_labels:
        group = [issue for issue in result["issues"] if issue["severity"] == severity]
        if not group:
            continue
        lines.append("")
        lines.append(f"{label} ({len(group)}):")
        for issue in group:
            lines.append(f"- [{issue['code']}] {issue['message']}")
            lines.append(f"  Path: {issue['path']}")
    return "\n".join(lines)


@click.command("lint", short_help="Report integrity and source-gardening issues.")
@root_option
@output_option
@pass_snowiki_context
def command(cli_context: SnowikiCliContext, root: Path | None, output: str) -> None:
    bind_cli_context(cli_context, root=root, output=output)
    output_mode = cli_context.output
    try:
        result = run_lint(initialize_cli_root(cli_context))
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="lint_failed")
    if result["error_count"]:
        emit_result(
            {"ok": False, "command": "lint", "result": result},
            output=output_mode,
            human_renderer=_render_lint_human,
        )
        raise click.exceptions.Exit(1)
    emit_command_result(
        result,
        command="lint",
        output=output_mode,
        human_renderer=_render_lint_human,
    )
