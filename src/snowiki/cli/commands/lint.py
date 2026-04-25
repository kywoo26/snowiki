from __future__ import annotations

from pathlib import Path
from typing import cast

import click

from snowiki.cli.decorators import output_option, root_option
from snowiki.cli.output import emit_error, emit_result, normalize_output_mode
from snowiki.config import get_snowiki_root
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


@click.command("lint")
@output_option
@root_option
def command(output: str, root: Path | None) -> None:
    output_mode = normalize_output_mode(output)
    try:
        result = run_lint(root if root else get_snowiki_root())
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="lint_failed")
    if result["error_count"]:
        emit_result(
            {"ok": False, "command": "lint", "result": result},
            output=output_mode,
            human_renderer=_render_lint_human,
        )
        raise click.exceptions.Exit(1)
    emit_result(
        {"ok": True, "command": "lint", "result": result},
        output=output_mode,
        human_renderer=_render_lint_human,
    )
