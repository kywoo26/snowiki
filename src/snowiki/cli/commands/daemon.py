from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from snowiki.config import get_snowiki_root
from snowiki.daemon.fallback import DaemonUnavailableError, daemon_request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
CACHE_TTL_DEFAULT = 30.0


def _host_option(func: Callable[..., object]) -> Callable[..., object]:
    return click.option(
        "--host",
        default=DEFAULT_HOST,
        envvar="SNOWIKI_DAEMON_HOST",
        show_default=True,
        show_envvar=True,
        help="Daemon bind host",
    )(func)


def _port_option(func: Callable[..., object]) -> Callable[..., object]:
    return click.option(
        "--port",
        type=click.IntRange(min=1, max=65535),
        default=DEFAULT_PORT,
        envvar="SNOWIKI_DAEMON_PORT",
        show_default=True,
        show_envvar=True,
        help="Daemon port",
    )(func)


def start_daemon(root: Path | None, host: str, port: int, cache_ttl: float) -> int:
    resolved_root = root.resolve() if root else get_snowiki_root()
    if _health(host, port) is not None:
        return 0

    _ = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "snowiki.daemon.server",
            "--root",
            str(resolved_root),
            "--host",
            host,
            "--port",
            str(port),
            "--cache-ttl",
            str(cache_ttl),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _health(host, port) is not None:
            return 0
        time.sleep(0.1)
    return 1


def stop_daemon(host: str, port: int) -> int:
    try:
        _ = daemon_request(
            _base_url(host, port),
            "/stop",
            method="POST",
            timeout=1.0,
        )
    except DaemonUnavailableError:
        return 0
    return 0


def daemon_status(host: str, port: int) -> dict[str, Any]:
    health = _health(host, port)
    if health is not None:
        return health
    return {
        "ok": False,
        "reachable": False,
        "host": host,
        "port": port,
    }


def status_daemon(host: str, port: int) -> int:
    return 0 if daemon_status(host, port)["ok"] is True else 1


def _health(host: str, port: int) -> dict[str, Any] | None:
    try:
        return daemon_request(_base_url(host, port), "/health", timeout=1.0)
    except DaemonUnavailableError:
        return None


def _base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


@click.group("daemon", no_args_is_help=True, short_help="Control the Snowiki daemon.")
def command() -> None:
    """Control the Snowiki daemon."""


@command.command("start", short_help="Start the Snowiki daemon.")
@click.option(
    "--root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    envvar="SNOWIKI_ROOT",
    show_envvar=True,
    help="Snowiki storage root (defaults to ~/.snowiki)",
)
@_host_option
@_port_option
@click.option(
    "--cache-ttl",
    type=click.FloatRange(min=0.0),
    default=CACHE_TTL_DEFAULT,
    envvar="SNOWIKI_DAEMON_CACHE_TTL",
    help="Query cache TTL in seconds",
    show_default=True,
    show_envvar=True,
)
def start_command(root: Path | None, host: str, port: int, cache_ttl: float) -> None:
    raise click.exceptions.Exit(start_daemon(root, host, port, cache_ttl))


@command.command("stop", short_help="Stop the Snowiki daemon.")
@_host_option
@_port_option
def stop_command(host: str, port: int) -> None:
    raise click.exceptions.Exit(stop_daemon(host, port))


@command.command("status", short_help="Check Snowiki daemon reachability.")
@_host_option
@_port_option
def status_command(host: str, port: int) -> None:
    raise click.exceptions.Exit(status_daemon(host, port))
