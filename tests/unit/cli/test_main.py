from __future__ import annotations

from importlib.metadata import version

import pytest
from click.testing import CliRunner

from snowiki.cli.main import app


def test_root_command_reports_package_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"snowiki, version {version('snowiki')}\n"


@pytest.mark.parametrize(
    ("shell", "expected"),
    [
        ("bash", "_snowiki_completion"),
        ("zsh", "#compdef snowiki"),
        ("fish", "complete --no-files --command snowiki"),
    ],
)
def test_root_command_emits_completion_script(shell: str, expected: str) -> None:
    result = CliRunner().invoke(
        app,
        [],
        env={"_SNOWIKI_COMPLETE": f"{shell}_source"},
    )

    assert result.exit_code == 0, result.output
    assert expected in result.output
