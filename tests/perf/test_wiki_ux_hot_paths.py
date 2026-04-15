from __future__ import annotations

import importlib.util
import socket
import statistics
import sys
import time
from pathlib import Path
from threading import Thread
from types import ModuleType
from typing import Any

from snowiki.cli.commands.ingest import run_ingest
from snowiki.daemon.fallback import DaemonUnavailableError, daemon_request
from snowiki.daemon.server import SnowikiDaemon


def _load_skill_script_module(name: str) -> ModuleType:
    module_path = Path(__file__).resolve().parents[2] / "skill" / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"wiki_perf_{name[:-3]}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load skill script module: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


QUERY_SCRIPT = _load_skill_script_module("query.py")
RECALL_SCRIPT = _load_skill_script_module("recall.py")

QUERY_TEXT = "claude-basic"
RECALL_TARGET = "2026-04-01"
MEASURED_RUNS = 5
WARM_LATENCY_CEILING_SECONDS = 0.5
WARM_BEATS_COLD_FACTOR = 0.95


def test_query_hot_path_prefers_warm_daemon_reads_over_cold_cli(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    _ = run_ingest(claude_basic_fixture, source="claude", root=tmp_path)

    daemon_port = _reserve_port()
    offline_port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=daemon_port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        _wait_for_health(daemon_port)
        warmup = QUERY_SCRIPT.run_query(
            QUERY_TEXT,
            root=tmp_path,
            host="127.0.0.1",
            port=daemon_port,
        )
        assert warmup["backend"] == "daemon"
        assert warmup["command"] == "query"
        assert warmup["result"]["query"] == QUERY_TEXT
        assert warmup["result"]["mode"] == "lexical"
        assert warmup["result"]["hits"]

        cold_payloads, cold_median = _measure_latency(
            lambda: QUERY_SCRIPT.run_query(
                QUERY_TEXT,
                root=tmp_path,
                host="127.0.0.1",
                port=offline_port,
            )
        )
        warm_payloads, warm_median = _measure_latency(
            lambda: QUERY_SCRIPT.run_query(
                QUERY_TEXT,
                root=tmp_path,
                host="127.0.0.1",
                port=daemon_port,
            )
        )

        assert all(payload["backend"] == "cli" for payload in cold_payloads)
        assert all(payload["backend"] == "daemon" for payload in warm_payloads)
        assert all(
            payload["result"]["query"] == QUERY_TEXT for payload in cold_payloads
        )
        assert all(
            payload["result"]["query"] == QUERY_TEXT for payload in warm_payloads
        )
        assert all(payload["result"]["mode"] == "lexical" for payload in warm_payloads)
        assert warm_median < cold_median * WARM_BEATS_COLD_FACTOR
        assert warm_median < WARM_LATENCY_CEILING_SECONDS
    finally:
        _stop_daemon(daemon_port)
        thread.join(timeout=5.0)


def test_recall_hot_path_prefers_warm_daemon_reads_over_cold_cli(
    tmp_path: Path, claude_basic_fixture: Path
) -> None:
    _ = run_ingest(claude_basic_fixture, source="claude", root=tmp_path)

    daemon_port = _reserve_port()
    offline_port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=daemon_port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        _wait_for_health(daemon_port)
        warmup = RECALL_SCRIPT.run_recall(
            RECALL_TARGET,
            root=tmp_path,
            host="127.0.0.1",
            port=daemon_port,
        )
        assert warmup["backend"] == "daemon"
        assert warmup["command"] == "recall"
        assert warmup["result"]["target"] == RECALL_TARGET
        assert warmup["result"]["strategy"] == "date"
        assert warmup["result"]["hits"]

        cold_payloads, cold_median = _measure_latency(
            lambda: RECALL_SCRIPT.run_recall(
                RECALL_TARGET,
                root=tmp_path,
                host="127.0.0.1",
                port=offline_port,
            )
        )
        warm_payloads, warm_median = _measure_latency(
            lambda: RECALL_SCRIPT.run_recall(
                RECALL_TARGET,
                root=tmp_path,
                host="127.0.0.1",
                port=daemon_port,
            )
        )

        assert all(payload["backend"] == "cli" for payload in cold_payloads)
        assert all(payload["backend"] == "daemon" for payload in warm_payloads)
        assert all(
            payload["result"]["target"] == RECALL_TARGET for payload in cold_payloads
        )
        assert all(
            payload["result"]["target"] == RECALL_TARGET for payload in warm_payloads
        )
        assert all(payload["result"]["strategy"] == "date" for payload in warm_payloads)
        assert warm_median < cold_median * WARM_BEATS_COLD_FACTOR
        assert warm_median < WARM_LATENCY_CEILING_SECONDS
    finally:
        _stop_daemon(daemon_port)
        thread.join(timeout=5.0)


def _measure_latency(
    operation: Any,
    *,
    iterations: int = MEASURED_RUNS,
) -> tuple[list[dict[str, Any]], float]:
    payloads: list[dict[str, Any]] = []
    samples: list[float] = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        payload = operation()
        samples.append(time.perf_counter() - started_at)
        payloads.append(payload)
    return payloads, statistics.median(samples)


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int) -> dict[str, Any]:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            health = daemon_request(f"http://127.0.0.1:{port}", "/health", timeout=1.0)
        except DaemonUnavailableError:
            time.sleep(0.05)
            continue
        if health.get("ok") is True:
            return health
    raise AssertionError("daemon health endpoint did not become ready")


def _stop_daemon(port: int) -> None:
    try:
        _ = daemon_request(
            f"http://127.0.0.1:{port}",
            "/stop",
            method="POST",
            timeout=1.0,
        )
    except DaemonUnavailableError:
        return
