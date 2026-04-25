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
    calls: list[list[str] | None] = []

    def fake_run(argv: list[str] | None = None) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(mcp_command, "run", fake_run)

    result = runner.invoke(app, ["mcp", "serve", "--stdio"])

    assert result.exit_code == 0, result.output
    assert calls == [["serve", "--stdio"]]


def test_mcp_serve_without_stdio_fails_closed() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "serve"])

    assert result.exit_code == 2
    assert "Only `snowiki mcp serve --stdio` is supported." in result.output
