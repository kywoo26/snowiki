from __future__ import annotations

import json
import socket
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
from click.testing import CliRunner
from tests.helpers.markdown_ingest import ingest_markdown_fixture
from tests.helpers.skill_modules import load_skill_script_module

from snowiki.cli.main import app
from snowiki.daemon.fallback import DaemonUnavailableError, daemon_request
from snowiki.daemon.server import SnowikiDaemon

pytestmark = pytest.mark.perf

QUERY_SCRIPT = load_skill_script_module("query.py", module_prefix="wiki_perf")
RECALL_SCRIPT = load_skill_script_module("recall.py", module_prefix="wiki_perf")

QUERY_TEXT = "claude-basic"
RECALL_TARGET = "2026-04-01"
MEASURED_RUNS = 5
WARM_LATENCY_CEILING_SECONDS = 0.5
WARM_BEATS_COLD_FACTOR = 0.95
STATUS_LINT_LATENCY_CEILING_SECONDS = 0.5


def test_query_hot_path_prefers_warm_daemon_reads_over_cold_cli(
    tmp_path: Path,
) -> None:
    _ = ingest_markdown_fixture(tmp_path)

    daemon_port = _reserve_port()
    offline_port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=daemon_port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        _ = _wait_for_health(daemon_port)
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
    tmp_path: Path,
) -> None:
    _ = ingest_markdown_fixture(tmp_path)

    daemon_port = _reserve_port()
    offline_port = _reserve_port()
    daemon = SnowikiDaemon(tmp_path, host="127.0.0.1", port=daemon_port)
    thread = Thread(target=daemon.serve_forever, daemon=True)
    thread.start()

    try:
        _ = _wait_for_health(daemon_port)
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


def test_status_hot_path_emits_stable_json_without_workspace_mutation(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _build_status_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    payloads, median_latency = _measure_latency(
        lambda: _invoke_json(runner, tmp_path, ["status", "--output", "json"])
    )

    assert _workspace_snapshot(tmp_path) == before
    assert median_latency < STATUS_LINT_LATENCY_CEILING_SECONDS
    assert all(payload["command"] == "status" for payload in payloads)
    assert all(payload["ok"] is True for payload in payloads)
    assert all("pages" in payload["result"] for payload in payloads)
    assert all("sources" in payload["result"] for payload in payloads)
    assert all("lint" in payload["result"] for payload in payloads)
    assert all("freshness" in payload["result"] for payload in payloads)
    assert all("manifest" in payload["result"] for payload in payloads)


def test_lint_hot_path_emits_stable_json_without_workspace_mutation(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    _build_lint_workspace(tmp_path)
    before = _workspace_snapshot(tmp_path)

    payloads, median_latency = _measure_latency(
        lambda: _invoke_json(runner, tmp_path, ["lint", "--output", "json"]),
    )

    assert _workspace_snapshot(tmp_path) == before
    assert median_latency < STATUS_LINT_LATENCY_CEILING_SECONDS
    assert all(payload["command"] == "lint" for payload in payloads)
    assert all(payload["ok"] is True for payload in payloads)
    assert all(
        payload["result"]["summary"]
        == {"error": 0, "warning": 1, "info": 0, "total": 1}
        for payload in payloads
    )
    assert all(payload["result"]["error_count"] == 0 for payload in payloads)
    assert all(
        payload["result"]["issues"][0]["check"] == "graph.orphan_compiled_page"
        for payload in payloads
    )


def _measure_latency(
    operation: Callable[[], dict[str, Any]],
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


def _invoke_json(runner: CliRunner, root: Path, args: list[str]) -> dict[str, Any]:
    result = runner.invoke(app, args, env={"SNOWIKI_ROOT": str(root)})
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


def _compiled_page(*, title: str, page_type: str, updated: str, body: str) -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            f'type: "{page_type}"',
            'created: "2026-04-15"',
            f'updated: "{updated}"',
            f'summary: "Summary for {title}"',
            "sources:",
            '  - "raw/claude/source-a.jsonl"',
            "related:",
            '  - "compiled/overview.md"',
            "tags:",
            f'  - "{page_type}"',
            "record_ids:",
            f'  - "{title.lower().replace(" ", "-")}"',
            "---",
            body,
        ]
    )


def _workspace_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix())
        if path.is_file()
    }


def _build_status_workspace(root: Path) -> None:
    _write_text(root / "raw" / "claude" / "source-a.jsonl", "{}\n")
    _write_text(root / "raw" / "opencode" / "source-b.jsonl", "{}\n")
    _write_json(
        root / "normalized" / "claude" / "2026-04-15" / "session-a.json",
        {
            "id": "session-a",
            "source_type": "claude",
            "record_type": "session",
            "recorded_at": "2026-04-15T09:00:00Z",
            "provenance": {"raw_refs": [{"path": "raw/claude/source-a.jsonl"}]},
        },
    )
    _write_json(
        root / "normalized" / "opencode" / "2026-04-16" / "session-b.json",
        {
            "id": "session-b",
            "source_type": "opencode",
            "record_type": "session",
            "recorded_at": "2026-04-16T08:30:00Z",
            "provenance": {"raw_refs": [{"path": "raw/opencode/source-b.jsonl"}]},
        },
    )

    _write_text(
        root / "compiled" / "overview.md",
        _compiled_page(
            title="Overview",
            page_type="overview",
            updated="2026-04-16",
            body="# Overview\n\n[[compiled/topics/wiki-dashboard]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "topics" / "wiki-dashboard.md",
        _compiled_page(
            title="Wiki Dashboard",
            page_type="topic",
            updated="2026-04-15",
            body="# Wiki Dashboard\n\n[[compiled/overview]]\n[[compiled/questions/what-is-status]]\n",
        ),
    )
    _write_text(
        root / "compiled" / "questions" / "what-is-status.md",
        _compiled_page(
            title="What Is Status",
            page_type="question",
            updated="2026-04-14",
            body="# What Is Status\n\n[[compiled/overview]]\n[[compiled/topics/wiki-dashboard]]\n",
        ),
    )

    _write_json(
        root / "index" / "manifest.json",
        {
            "records_indexed": 2,
            "pages_indexed": 3,
            "search_documents": 5,
            "compiled_paths": [
                "compiled/overview.md",
                "compiled/questions/what-is-status.md",
                "compiled/topics/wiki-dashboard.md",
            ],
        },
    )


def _build_lint_workspace(root: Path) -> None:
    _write_text(root / "compiled" / "overview.md", _frontmatter_page(title="Overview"))
    _write_text(
        root / "compiled" / "topics" / "orphaned.md",
        _frontmatter_page(title="Orphaned"),
    )
    _write_json(root / "index" / "manifest.json", {"pages": ["overview.md"]})


def _frontmatter_page(*, title: str, body: str = "# Page\n") -> str:
    return "\n".join(
        [
            "---",
            f'title: "{title}"',
            'type: "topic"',
            'created: "2026-04-16"',
            'updated: "2026-04-16"',
            'summary: "Summary"',
            "sources:",
            '  - "raw/claude/source.jsonl"',
            "related: []",
            "tags: []",
            "record_ids:",
            '  - "record-1"',
            "---",
            body,
        ]
    )


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
