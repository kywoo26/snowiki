from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from snowiki.cli.commands import daemon as daemon_module


def test_click_group_documents_subcommands() -> None:
    result = CliRunner().invoke(daemon_module.command, ["--help"])

    assert result.exit_code == 0, result.output
    assert "start" in result.output
    assert "stop" in result.output
    assert "status" in result.output


def test_click_group_dispatches_to_selected_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    def fake_start(root: Path | None, host: str, port: int, cache_ttl: float) -> int:
        _ = (root, host, port, cache_ttl)
        called.append("start")
        return 10

    def fake_stop(host: str, port: int) -> int:
        _ = (host, port)
        called.append("stop")
        return 20

    def fake_status(host: str, port: int) -> int:
        _ = (host, port)
        called.append("status")
        return 30

    monkeypatch.setattr(daemon_module, "start_daemon", fake_start)
    monkeypatch.setattr(daemon_module, "stop_daemon", fake_stop)
    monkeypatch.setattr(daemon_module, "status_daemon", fake_status)

    runner = CliRunner()

    assert runner.invoke(daemon_module.command, ["start"]).exit_code == 10
    assert runner.invoke(daemon_module.command, ["stop"]).exit_code == 20
    assert runner.invoke(daemon_module.command, ["status"]).exit_code == 30
    assert called == ["start", "stop", "status"]


def test_start_command_returns_zero_when_daemon_is_already_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(daemon_module, "_health", lambda host, port: {"ok": True})
    popen_calls: list[object] = []
    monkeypatch.setattr(
        daemon_module.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    assert daemon_module.start_daemon(Path("."), "127.0.0.1", 8765, 30.0) == 0
    assert popen_calls == []


def test_start_command_launches_process_and_waits_for_health(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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

    assert daemon_module.start_daemon(tmp_path, "127.0.0.1", 9999, 12.5) == 0
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
    monotonic_values = iter((0.0, 6.0))

    monkeypatch.setattr(daemon_module, "_health", lambda host, port: None)
    monkeypatch.setattr(daemon_module.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(daemon_module.subprocess, "Popen", lambda *args, **kwargs: None)

    assert daemon_module.start_daemon(Path("."), "127.0.0.1", 8765, 30.0) == 1


def test_stop_and_status_commands_handle_available_and_unavailable_daemon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[str, str, str, float]] = []
    health_payload: dict[str, object] = {
        "ok": True,
        "pid": 1234,
        "host": "127.0.0.1",
        "port": 8765,
        "cache": {"owner": "daemon.response_cache", "kind": "ttl_response_cache"},
        "indexes": {
            "owner": "daemon.warm_indexes",
            "generation": 4,
            "freshness": {
                "snapshot_owner": "daemon.warm_indexes",
                "runtime_generation": 4,
            },
        },
    }

    def fake_request(
        base_url: str, path: str, *, method: str = "GET", timeout: float
    ) -> dict[str, object]:
        requests.append((base_url, path, method, timeout))
        return health_payload

    monkeypatch.setattr(daemon_module, "daemon_request", fake_request)
    monkeypatch.setattr(daemon_module, "_health", lambda host, port: health_payload)

    assert daemon_module.stop_daemon("127.0.0.1", 8765) == 0
    assert daemon_module.status_daemon("127.0.0.1", 8765) == 0
    assert daemon_module.daemon_status("127.0.0.1", 8765) == health_payload
    assert requests == [("http://127.0.0.1:8765", "/stop", "POST", 1.0)]

    def raise_unavailable(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise daemon_module.DaemonUnavailableError("offline")

    monkeypatch.setattr(daemon_module, "daemon_request", raise_unavailable)
    monkeypatch.setattr(daemon_module, "_health", lambda host, port: None)

    assert daemon_module.stop_daemon("127.0.0.1", 8765) == 0
    assert daemon_module.status_daemon("127.0.0.1", 8765) == 1
    assert daemon_module.daemon_status("127.0.0.1", 8765) == {
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


def test_click_start_command_invokes_daemon_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[Path | None, str, int, float]] = []
    runner = CliRunner()

    def fake_start(root: Path | None, host: str, port: int, cache_ttl: float) -> int:
        captured.append((root, host, port, cache_ttl))
        return 0

    monkeypatch.setattr(daemon_module, "start_daemon", fake_start)

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
    assert captured == [(None, "0.0.0.0", 9000, 45.0)]
