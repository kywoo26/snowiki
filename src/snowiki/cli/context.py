from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click

from snowiki.cli.output import OutputMode, normalize_output_mode
from snowiki.config import resolve_snowiki_root


@dataclass
class SnowikiCliContext:
    """Shared Click invocation state for Snowiki command adapters."""

    root: Path | None = None
    output: OutputMode = "human"


pass_snowiki_context = click.make_pass_decorator(SnowikiCliContext, ensure=True)


def ensure_snowiki_context(ctx: click.Context) -> SnowikiCliContext:
    """Ensure the root Click context carries Snowiki adapter state."""

    return ctx.ensure_object(SnowikiCliContext)


def bind_cli_context(
    cli_context: SnowikiCliContext,
    *,
    root: Path | None,
    output: str,
) -> SnowikiCliContext:
    """Bind parsed command options into shared adapter state.

    This is intentionally side-effect free. Storage directory creation belongs
    inside command execution paths after command-local validation has passed.
    """

    cli_context.output = normalize_output_mode(output)
    cli_context.root = root
    return cli_context


def initialize_cli_root(cli_context: SnowikiCliContext) -> Path:
    """Resolve and prepare the Snowiki root for commands that need storage."""

    cli_context.root = resolve_snowiki_root(cli_context.root)
    return cli_context.root


def require_cli_root(cli_context: SnowikiCliContext) -> Path:
    """Return the bound storage root for commands that initialize storage."""

    if cli_context.root is None:
        raise click.ClickException("Snowiki root was not initialized for this command")
    return cli_context.root


def root_parameter_source(ctx: click.Context) -> click.core.ParameterSource | None:
    """Return how Click resolved the shared root option for the current command."""

    return ctx.get_parameter_source("root")
