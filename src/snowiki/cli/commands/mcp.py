from __future__ import annotations

import argparse
import importlib
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, BinaryIO

import click


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Snowiki MCP commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Serve Snowiki over MCP")
    serve_parser.add_argument(
        "--stdio",
        action="store_true",
        help="Serve the read-only MCP facade over stdio.",
    )
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    session_records: Sequence[Mapping[str, Any]] = (),
    compiled_pages: Sequence[Mapping[str, Any]] = (),
    reference_time: datetime | None = None,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command != "serve" or not args.stdio:
        parser.error("Only `snowiki mcp serve --stdio` is supported.")

    mcp_module = importlib.import_module("snowiki.mcp")
    create_server = mcp_module.create_server
    serve_stdio = mcp_module.serve_stdio
    server = create_server(
        session_records=session_records,
        compiled_pages=compiled_pages,
        reference_time=reference_time,
    )
    serve_stdio(server, input_stream=input_stream, output_stream=output_stream)
    return 0


@click.group("mcp", no_args_is_help=True, short_help="Serve Snowiki over MCP.")
def command() -> None:
    """Snowiki MCP commands."""


@command.command("serve", short_help="Serve the read-only MCP facade.")
@click.option(
    "--stdio",
    is_flag=True,
    help="Serve the read-only MCP facade over stdio.",
)
def serve_command(stdio: bool) -> None:
    argv: list[str] = ["serve"]
    if stdio:
        argv.append("--stdio")
    raise click.exceptions.Exit(run(argv))
