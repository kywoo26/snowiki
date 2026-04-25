from __future__ import annotations

from importlib.metadata import version

from click.testing import CliRunner

from snowiki.cli.main import app


def test_root_command_reports_package_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"snowiki, version {version('snowiki')}\n"


def test_root_command_emits_bash_completion_script() -> None:
    result = CliRunner().invoke(
        app,
        [],
        env={"_SNOWIKI_COMPLETE": "bash_source"},
    )

    assert result.exit_code == 0, result.output
    assert "_snowiki_completion" in result.output
    assert "complete -o nosort -F _snowiki_completion snowiki" in result.output
