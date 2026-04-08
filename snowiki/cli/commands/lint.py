from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from snowiki.cli.output import OutputMode, emit_error, emit_result


def _normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def run_lint(root: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for path in sorted(
        (root / "normalized").rglob("*.json"), key=lambda item: item.as_posix()
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                {
                    "code": "LJSON",
                    "severity": "error",
                    "path": path.relative_to(root).as_posix(),
                    "message": str(exc),
                }
            )
            continue
        for key in ("id", "source_type", "record_type"):
            if key not in payload:
                issues.append(
                    {
                        "code": "L001",
                        "severity": "error",
                        "path": path.relative_to(root).as_posix(),
                        "message": f"missing required key: {key}",
                    }
                )
    for path in sorted(
        (root / "compiled").rglob("*.md"), key=lambda item: item.as_posix()
    ):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text:
            issues.append(
                {
                    "code": "L002",
                    "severity": "error",
                    "path": path.relative_to(root).as_posix(),
                    "message": "compiled page missing YAML frontmatter",
                }
            )
    return {
        "root": root.as_posix(),
        "issues": issues,
        "error_count": sum(1 for issue in issues if issue["severity"] == "error"),
    }


def _render_lint_human(payload: dict[str, Any]) -> str:
    result = payload["result"]
    if not result["issues"]:
        return f"Lint passed for {result['root']}"
    lines = [f"Lint found {len(result['issues'])} issue(s):"]
    lines.extend(
        f"- {issue['code']} {issue['path']}: {issue['message']}"
        for issue in result["issues"]
    )
    return "\n".join(lines)


@click.command("lint")
@click.option(
    "--output",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def command(output: str) -> None:
    output_mode = _normalize_output_mode(output)
    result: dict[str, Any] | None = None
    try:
        result = run_lint(Path.cwd())
    except Exception as exc:
        emit_error(str(exc), output=output_mode, code="lint_failed")
    if result is None:
        raise RuntimeError("lint did not produce a result")
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
