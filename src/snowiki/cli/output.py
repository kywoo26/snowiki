from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, NoReturn

import click

OutputMode = Literal["human", "json"]


def normalize_output_mode(value: str) -> OutputMode:
    return "json" if value == "json" else "human"


def emit_result(
    payload: dict[str, Any],
    *,
    output: OutputMode,
    human_renderer: Callable[[dict[str, Any]], str] | None = None,
) -> None:
    if output == "json":
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return
    if human_renderer is not None:
        click.echo(human_renderer(payload))
        return
    click.echo(str(payload.get("message", "")))


def emit_command_result(
    result: object,
    *,
    command: str,
    output: OutputMode,
    human_renderer: Callable[[dict[str, Any]], str] | None = None,
) -> None:
    """Emit a standard successful Snowiki command envelope."""

    emit_result(
        {"ok": True, "command": command, "result": result},
        output=output,
        human_renderer=human_renderer,
    )


def emit_error(
    message: str,
    *,
    output: OutputMode,
    code: str = "error",
    details: dict[str, Any] | None = None,
    exit_code: int = 1,
) -> NoReturn:
    error_payload: dict[str, object] = {
        "code": code,
        "message": message,
    }
    if details:
        error_payload["details"] = details
    payload: dict[str, object] = {
        "ok": False,
        "error": error_payload,
    }
    if output == "json":
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        click.echo(f"Error: {message}", err=True)
    raise click.exceptions.Exit(exit_code)


def validate_destructive_flags(
    *,
    dry_run: bool,
    delete_artifacts: bool,
    yes: bool,
    output: OutputMode,
    code: str,
    conflict_code: str | None = None,
    confirmation_message: str = "deletion requires --yes",
) -> None:
    """Validate standard dry-run/delete/yes destructive option contracts."""

    if dry_run and delete_artifacts:
        emit_error(
            "--dry-run cannot be combined with --delete",
            output=output,
            code=conflict_code or code,
        )
    if delete_artifacts and not yes:
        emit_error(confirmation_message, output=output, code=code)
