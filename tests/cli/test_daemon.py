from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from click.testing import CliRunner
from snowiki.cli.commands import daemon as daemon_module


def test_build_parser_uses_expected_defaults() -> None:
    args = daemon_module.build_parser().parse_args(["status"])

    assert args.action == "status"
    assert args.root is None
    assert args.host == daemon_module.DEFAULT_HOST
    assert args.port == daemon_module.DEFAULT_PORT
    assert args.cache_ttl == 30.0


def test_main_dispatches_to_selected_action(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[tuple[str, str]] = []

    def fake_start(args: Namespace) -> int:
        called.append(("start", args.action))
        return 10

    def fake_stop(args: Namespace) -> int:
        called.append(("stop", args.action))
        return 20

    def fake_status(args: Namespace) -> int:
        called.append(("status", args.action))
        return 30

    monkeypatch.setattr(daemon_module, "start_command", fake_start)
    monkeypatch.setattr(daemon_module, "stop_command", fake_stop)
    monkeypatch.setattr(daemon_module, "status_command", fake_status)

    assert daemon_module.main(["start"]) == 10
    assert daemon_module.main(["stop"]) == 20
    assert daemon_module.main(["status"]) == 30
    assert called == [("start", "start"), ("stop", "stop"), ("status", "status")]


def test_start_command_returns_zero_when_daemon_is_already_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = Namespace(
        action="start",
        root=".",
        host="127.0.0.1",
        port=8765,
        cache_ttl=30.0,
    )

    monkeypatch.setattr(daemon_module, "_health", lambda host, port: {"ok": True})
    popen_calls: list[object] = []
    monkeypatch.setattr(
        daemon_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    assert daemon_module.start_command(args) == 0
    assert popen_calls == []


def test_start_command_launches_process_and_waits_for_health(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    args = Namespace(
        action="start",
        root=str(tmp_path),
        host="127.0.0.1",
        port=9999,
        cache_ttl=12.5,
    )
    health_checks = iter((None, {"ok": True}))
    popen_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(
        daemon_module,
        "_health",
        lambda host, port: next(health_checks),
    )
    monkeypatch.setattr(daemon_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        daemon_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    assert daemon_module.start_command(args) == 0
    assert len(popen_calls) == 1
    command = popen_calls[0][0][0]
    assert command == [
        daemon_module.sys.executable,
        "-m",
        "snowiki.daemon.server",
        "--root",
        str(tmp_path.resolve()),
        "--host",
        "127.0.0.1",
        "--port",
        "9999",
        "--cache-ttl",
        "12.5",
    ]
    assert popen_calls[0][1] == {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "start_new_session": True,
    }


def test_start_command_returns_one_when_health_never_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = Namespace(
        action="start",
        root=".",
        host="127.0.0.1",
        port=8765,
        cache_ttl=30.0,
    )
    monotonic_values = iter((0.0, 6.0))

    monkeypatch.setattr(daemon_module, "_health", lambda host, port: None)
    monkeypatch.setattr(daemon_module.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(daemon_module.subprocess, "Popen", lambda *args, **kwargs: None)

    assert daemon_module.start_command(args) == 1


def test_stop_and_status_commands_handle_available_and_unavailable_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = Namespace(
        action="status",
        root=".",
        host="127.0.0.1",
        port=8765,
        cache_ttl=30.0,
    )
    requests: list[tuple[str, str, str, float]] = []

    def fake_request(
        base_url: str, path: str, *, method: str = "GET", timeout: float
    ) -> dict[str, object]:
        requests.append((base_url, path, method, timeout))
        return {"ok": True, "reachable": True}

    monkeypatch.setattr(daemon_module, "daemon_request", fake_request)
    monkeypatch.setattr(daemon_module, "_health", lambda host, port: {"ok": True})

    assert daemon_module.stop_command(args) == 0
    assert daemon_module.status_command(args) == 0
    assert daemon_module.daemon_status(args) == {"ok": True}
    assert requests == [("http://127.0.0.1:8765", "/stop", "POST", 1.0)]

    def raise_unavailable(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise daemon_module.DaemonUnavailableError("offline")

    monkeypatch.setattr(daemon_module, "daemon_request", raise_unavailable)
    monkeypatch.setattr(daemon_module, "_health", lambda host, port: None)

    assert daemon_module.stop_command(args) == 0
    assert daemon_module.status_command(args) == 1
    assert daemon_module.daemon_status(args) == {
        "ok": False,
        "reachable": False,
        "host": "127.0.0.1",
        "port": 8765,
    }


def test_health_wraps_daemon_unavailable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        daemon_module,
        "daemon_request",
        lambda base_url, path, timeout: {
            "ok": True,
            "base_url": base_url,
            "path": path,
        },
    )
    assert daemon_module._health("localhost", 1234) == {
        "ok": True,
        "base_url": "http://localhost:1234",
        "path": "/health",
    }

    def raise_unavailable(
        _base_url: str, _path: str, *, timeout: float
    ) -> dict[str, object]:
        _ = timeout
        raise daemon_module.DaemonUnavailableError("offline")

    monkeypatch.setattr(daemon_module, "daemon_request", raise_unavailable)
    assert daemon_module._health("localhost", 1234) is None
    assert daemon_module._base_url("localhost", 1234) == "http://localhost:1234"


def test_click_command_forwards_args_into_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []
    runner = CliRunner()

    def fake_main(argv: list[str] | None = None) -> int:
        captured.append([] if argv is None else argv)
        return 0

    monkeypatch.setattr(daemon_module, "main", fake_main)

    result = runner.invoke(
        daemon_module.command,
        [
            "start",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--cache-ttl",
            "45",
        ],
    )

    assert result.exit_code == 0
    assert captured == [
        ["start", "--host", "0.0.0.0", "--port", "9000", "--cache-ttl", "45.0"]
    ]
