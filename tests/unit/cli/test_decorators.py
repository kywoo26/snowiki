from __future__ import annotations

from pathlib import Path

import click
from click.testing import CliRunner

from snowiki.cli.decorators import output_option, root_option


@click.command("decorated")
@output_option
@root_option
def decorated_command(output: str, root: Path | None) -> None:
    click.echo(f"output={output}")
    click.echo(f"root={root.as_posix() if root else 'none'}")


def test_output_and_root_options_apply_standard_click_contract(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        decorated_command,
        ["--output", "json", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert result.output == f"output=json\nroot={tmp_path.as_posix()}\n"


def test_output_option_rejects_unknown_mode() -> None:
    result = CliRunner().invoke(decorated_command, ["--output", "yaml"])

    assert result.exit_code == 2
    assert "Invalid value for '--output'" in result.output


def test_decorated_help_documents_shared_options() -> None:
    result = CliRunner().invoke(decorated_command, ["--help"])

    assert result.exit_code == 0
    assert "--output [human|json]" in result.output
    assert "--root DIRECTORY" in result.output
