from __future__ import annotations

from pathlib import Path

import click
from click.testing import CliRunner

from snowiki.cli.context import root_parameter_source
from snowiki.cli.decorators import output_option, root_option


@click.command("decorated")
@output_option
@root_option
def decorated_command(output: str, root: Path | None) -> None:
    click.echo(f"output={output}")
    click.echo(f"root={root.as_posix() if root else 'none'}")


@click.command("source-aware")
@root_option
@click.pass_context
def source_aware_command(ctx: click.Context, root: Path | None) -> None:
    source = root_parameter_source(ctx)
    click.echo(f"root={root.as_posix() if root else 'none'}")
    click.echo(f"source={source.name if source else 'none'}")


def test_output_and_root_options_apply_standard_click_contract(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        decorated_command,
        ["--output", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert result.output == f"output=json\nroot={tmp_path.as_posix()}\n"


def test_root_option_reads_snowiki_root_envvar(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        decorated_command,
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert result.output == f"output=human\nroot={tmp_path.as_posix()}\n"


def test_output_option_reads_snowiki_output_envvar() -> None:
    result = CliRunner().invoke(
        decorated_command,
        env={"SNOWIKI_OUTPUT": "json"},
    )

    assert result.exit_code == 0, result.output
    assert result.output == "output=json\nroot=none\n"


def test_root_parameter_source_reports_environment(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        source_aware_command,
        env={"SNOWIKI_ROOT": str(tmp_path)},
    )

    assert result.exit_code == 0, result.output
    assert result.output == f"root={tmp_path.as_posix()}\nsource=ENVIRONMENT\n"


def test_output_option_rejects_unknown_mode() -> None:
    result = CliRunner().invoke(decorated_command, ["--output", "yaml"])

    assert result.exit_code == 2
    assert "Invalid value for '--output'" in result.output


def test_decorated_help_documents_shared_options() -> None:
    result = CliRunner().invoke(decorated_command, ["--help"])

    assert result.exit_code == 0
    assert "--output [human|json]" in result.output
    assert "--root DIRECTORY" in result.output
    assert "env var: SNOWIKI_ROOT" in " ".join(result.output.split())
    assert "env var: SNOWIKI_OUTPUT" in " ".join(result.output.split())
