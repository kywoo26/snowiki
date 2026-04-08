from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, NoReturn

import click

OutputMode = Literal["human", "json"]


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


def emit_error(
    message: str,
    *,
    output: OutputMode,
    code: str = "error",
    details: dict[str, Any] | None = None,
    exit_code: int = 1,
) -> NoReturn:
    payload: dict[str, Any] = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    if output == "json":
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        click.echo(f"Error: {message}", err=True)
    raise click.exceptions.Exit(exit_code)
