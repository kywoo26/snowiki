from __future__ import annotations

import socket
import time
from pathlib import Path
from threading import Thread
from typing import cast

import pytest

pytestmark = pytest.mark.integration


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
        indexes_dict = cast(dict[str, object], indexes)
        blended_size = indexes_dict.get("blended_size")
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
