from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click

from snowiki.daemon.fallback import DaemonUnavailableError, daemon_request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="snowiki daemon")
    parser.add_argument("action", choices=("start", "stop", "status"))
    parser.add_argument("--root", default=".", help="Snowiki storage root")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Daemon bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Daemon port")
    parser.add_argument(
        "--cache-ttl",
        type=float,
        default=30.0,
        help="Query cache TTL in seconds",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "start":
        return start_command(args)
    if args.action == "stop":
        return stop_command(args)
    return status_command(args)


def start_command(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if _health(args.host, args.port) is not None:
        return 0

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "snowiki.daemon.server",
            "--root",
            str(root),
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--cache-ttl",
            str(args.cache_ttl),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _health(args.host, args.port) is not None:
            return 0
        time.sleep(0.1)
    return 1


def stop_command(args: argparse.Namespace) -> int:
    try:
        daemon_request(
            _base_url(args.host, args.port),
            "/stop",
            method="POST",
            timeout=1.0,
        )
    except DaemonUnavailableError:
        return 0
    return 0


def status_command(args: argparse.Namespace) -> int:
    return 0 if _health(args.host, args.port) is not None else 1


def daemon_status(args: argparse.Namespace) -> dict[str, Any]:
    health = _health(args.host, args.port)
    if health is not None:
        return health
    return {
        "ok": False,
        "reachable": False,
        "host": args.host,
        "port": args.port,
    }


def _health(host: str, port: int) -> dict[str, Any] | None:
    try:
        return daemon_request(_base_url(host, port), "/health", timeout=1.0)
    except DaemonUnavailableError:
        return None


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


if __name__ == "__main__":
    raise SystemExit(main())


@click.command("daemon")
@click.argument("action", type=click.Choice(("start", "stop", "status")))
@click.option("--root", default=".", help="Snowiki storage root")
@click.option("--host", default=DEFAULT_HOST, help="Daemon bind host")
@click.option("--port", type=int, default=DEFAULT_PORT, help="Daemon port")
@click.option(
    "--cache-ttl",
    type=float,
    default=30.0,
    help="Query cache TTL in seconds",
)
def command(action: str, root: str, host: str, port: int, cache_ttl: float) -> None:
    argv = [
        action,
        "--root",
        root,
        "--host",
        host,
        "--port",
        str(port),
        "--cache-ttl",
        str(cache_ttl),
    ]
    raise SystemExit(main(argv))
