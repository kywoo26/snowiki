from __future__ import annotations

import pytest
from click.testing import CliRunner

from snowiki.cli.commands import mcp as mcp_command
from snowiki.cli.main import app


def test_mcp_help_lists_readonly_stdio_surface() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "serve", "--help"])

    assert result.exit_code == 0, result.output
    assert "--stdio" in result.output
    assert "Serve the read-only MCP facade over stdio." in result.output


def test_mcp_serve_stdio_forwards_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    calls: list[bool] = []

    def fake_serve_stdio_command(**_kwargs: object) -> int:
        calls.append(True)
        return 0

    monkeypatch.setattr(mcp_command, "serve_stdio_command", fake_serve_stdio_command)

    result = runner.invoke(app, ["mcp", "serve", "--stdio"])

    assert result.exit_code == 0, result.output
    assert calls == [True]


def test_mcp_serve_without_stdio_fails_closed() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "serve"])

    assert result.exit_code == 2
    assert "Only `snowiki mcp serve --stdio` is supported." in result.output
