from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click


def output_option(func: Callable[..., object]) -> Callable[..., object]:
    """Apply the standard Snowiki human/json output option."""
    decorator = click.option(
        "--output",
        type=click.Choice(["human", "json"], case_sensitive=False),
        default="human",
        show_default=True,
    )
    return decorator(func)


def root_option(func: Callable[..., object]) -> Callable[..., object]:
    """Apply the standard Snowiki storage root option."""
    decorator = click.option(
        "--root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help="Snowiki storage root (defaults to ~/.snowiki)",
    )
    return decorator(func)
