from __future__ import annotations

import socket
import time
from pathlib import Path
from threading import Thread
from typing import cast

import pytest

pytestmark = pytest.mark.integration


def test_query_endpoint_handles_iso_date_recall_and_stop_returns_full_json(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    from snowiki.cli.commands.ingest import run_ingest
    from snowiki.daemon.fallback import daemon_request
    from snowiki.daemon.server import SnowikiDaemon

    _ = run_ingest(claude_basic_fixture, source="claude", root=tmp_path)

    port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        _wait_for_health(port)
        recall = daemon_request(
            f"http://127.0.0.1:{port}",
            "/query",
            method="POST",
            payload={"operation": "recall", "query": "2026-04-01", "limit": 5},
            timeout=1.0,
        )
        assert recall["ok"] is True
        assert recall["operation"] == "recall"
        assert recall["strategy"] == "date"
        recall_hits = cast(list[dict[str, object]], recall["hits"])
        assert recall_hits
        assert all("2026/04/01" in str(hit["path"]) for hit in recall_hits)

        stop = daemon_request(
            f"http://127.0.0.1:{port}",
            "/stop",
            method="POST",
            timeout=1.0,
        )
        assert stop["ok"] is True
        assert stop["stopping"] is True
        assert isinstance(stop["pid"], int)
    finally:
        thread.join(timeout=5.0)


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
        assert indexes_dict["owner"] == "daemon.warm_indexes"
        assert isinstance(indexes_dict["generation"], int)
        freshness = cast(dict[str, object], indexes_dict.get("freshness"))
        assert freshness["snapshot_owner"] == "daemon.warm_indexes"
        blended_size = indexes_dict.get("blended_size")
        assert isinstance(blended_size, int)
        assert blended_size >= 1

        status = daemon_request(
            f"http://127.0.0.1:{port}",
            "/status",
            timeout=1.0,
        )
        assert status["ok"] is True
        status_indexes = cast(dict[str, object], status["indexes"])
        assert status_indexes["owner"] == "daemon.warm_indexes"
        assert isinstance(status_indexes["generation"], int)
        assert status_indexes == indexes
        assert status["started_at"].endswith("Z")
        assert status["url"] == f"http://127.0.0.1:{port}"
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
