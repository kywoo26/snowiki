from __future__ import annotations

from datetime import timedelta

import click
from click.testing import CliRunner

from snowiki.cli.types import DURATION


@click.command("duration")
@click.option("--older-than", type=DURATION, required=True)
def duration_command(older_than: timedelta) -> None:
    click.echo(str(int(older_than.total_seconds())))


def test_duration_param_type_parses_supported_units() -> None:
    runner = CliRunner()

    assert runner.invoke(duration_command, ["--older-than", "2d"]).output == "172800\n"
    assert runner.invoke(duration_command, ["--older-than", "3h"]).output == "10800\n"
    assert runner.invoke(duration_command, ["--older-than", "45s"]).output == "45\n"


def test_duration_param_type_rejects_invalid_units() -> None:
    result = CliRunner().invoke(duration_command, ["--older-than", "10w"])

    assert result.exit_code == 2
    assert "duration must use a positive integer plus d, h, or s" in result.output
