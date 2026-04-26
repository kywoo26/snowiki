from __future__ import annotations

from datetime import timedelta

import click
from click.testing import CliRunner

from snowiki.cli.types import DURATION, PROPOSAL_ID


@click.command("duration")
@click.option("--older-than", type=DURATION, required=True)
def duration_command(older_than: timedelta) -> None:
    click.echo(str(int(older_than.total_seconds())))


@click.command("proposal")
@click.argument("proposal_id", type=PROPOSAL_ID)
def proposal_command(proposal_id: str) -> None:
    click.echo(proposal_id)


def test_duration_param_type_parses_supported_units() -> None:
    runner = CliRunner()

    assert runner.invoke(duration_command, ["--older-than", "2d"]).output == "172800\n"
    assert runner.invoke(duration_command, ["--older-than", "3h"]).output == "10800\n"
    assert runner.invoke(duration_command, ["--older-than", "45s"]).output == "45\n"


def test_duration_param_type_rejects_invalid_units() -> None:
    result = CliRunner().invoke(duration_command, ["--older-than", "10w"])

    assert result.exit_code == 2
    assert "duration must use a positive integer plus d, h, or s" in result.output


def test_duration_param_type_passes_through_timedelta_defaults() -> None:
    @click.command("default-duration")
    @click.option("--older-than", type=DURATION, default=timedelta(hours=2))
    def default_duration_command(older_than: timedelta) -> None:
        click.echo(str(int(older_than.total_seconds())))

    result = CliRunner().invoke(default_duration_command, [])

    assert result.exit_code == 0, result.output
    assert result.output == "7200\n"


def test_proposal_id_param_type_accepts_canonical_ids() -> None:
    result = CliRunner().invoke(
        proposal_command,
        ["fileback-proposal-0123456789abcdef"],
    )

    assert result.exit_code == 0, result.output
    assert result.output == "fileback-proposal-0123456789abcdef\n"


def test_proposal_id_param_type_rejects_malformed_ids() -> None:
    result = CliRunner().invoke(proposal_command, ["proposal-123"])

    assert result.exit_code == 2
    assert "proposal id must match fileback-proposal-<16 lowercase hex chars>" in result.output
