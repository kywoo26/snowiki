from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from snowiki.config import SNOWIKI_ROOT_ENV_VAR

SNOWIKI_OUTPUT_ENV_VAR = "SNOWIKI_OUTPUT"


def output_option(func: Callable[..., object]) -> Callable[..., object]:
    """Apply the standard Snowiki human/json output option."""
    decorator = click.option(
        "--output",
        type=click.Choice(["human", "json"], case_sensitive=False),
        default="human",
        envvar=SNOWIKI_OUTPUT_ENV_VAR,
        show_envvar=True,
        show_default=True,
    )
    return decorator(func)


def root_option(func: Callable[..., object]) -> Callable[..., object]:
    """Apply the standard Snowiki storage root option."""
    decorator = click.option(
        "--root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        envvar=SNOWIKI_ROOT_ENV_VAR,
        show_envvar=True,
        help="Snowiki storage root (defaults to ~/.snowiki)",
    )
    return decorator(func)
