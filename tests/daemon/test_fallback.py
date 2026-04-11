from __future__ import annotations

import socket
import time
from pathlib import Path
from threading import Thread

import pytest


@pytest.fixture(autouse=True)
def _add_repo_root_to_sys_path(repo_root: Path) -> None:
    import sys

    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def test_execute_with_fallback_uses_fallback_when_daemon_is_unavailable() -> None:
    from snowiki.daemon.fallback import DaemonUnavailableError, execute_with_fallback

    def daemon_call() -> object:
        raise DaemonUnavailableError("connection refused")

    result = execute_with_fallback(
        daemon_call,
        lambda: {"answer": "local-cli-result"},
    )

    assert result == {
        "mode": "fallback",
        "result": {"answer": "local-cli-result"},
    }


def test_execute_with_fallback_prefers_daemon_result_when_available() -> None:
    from snowiki.daemon.fallback import execute_with_fallback

    result = execute_with_fallback(
        lambda: {"answer": "daemon-result"},
        lambda: {"answer": "local-cli-result"},
    )

    assert result == {
        "mode": "daemon",
        "result": {"answer": "daemon-result"},
    }


def test_health_endpoint_reports_ok_when_daemon_is_running(tmp_path: Path) -> None:
    from snowiki.daemon.fallback import daemon_request
    from snowiki.daemon.server import SnowikiDaemon

    port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        health = _wait_for_health(port)
        assert health["ok"] is True
        indexes = health["indexes"]
        assert isinstance(indexes, dict)
        indexes_dict = indexes
        blended_size = indexes_dict.get("blended_size")  # type: ignore
        assert isinstance(blended_size, int)
        assert blended_size >= 1
    finally:
        _ = daemon_request(
            f"http://127.0.0.1:{port}",
            "/stop",
            method="POST",
            timeout=1.0,
        )
        thread.join(timeout=5.0)


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int) -> dict[str, object]:
    from snowiki.daemon.fallback import DaemonUnavailableError, daemon_request

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            return daemon_request(
                f"http://127.0.0.1:{port}",
                "/health",
                timeout=1.0,
            )
        except DaemonUnavailableError:
            time.sleep(0.05)
    raise AssertionError("daemon health endpoint did not become ready")
