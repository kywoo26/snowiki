from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

import pytest


def _load_read_router_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[2] / "skill" / "scripts" / "read_router.py"
    )
    spec = importlib.util.spec_from_file_location("wiki_read_router", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load wiki read router module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_skill_script_module(name: str) -> ModuleType:
    module_path = Path(__file__).resolve().parents[2] / "skill" / "scripts" / name
    spec = importlib.util.spec_from_file_location(
        f"wiki_skill_{name[:-3]}", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load skill script module: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


READ_ROUTER = _load_read_router_module()
QUERY_SCRIPT = _load_skill_script_module("query.py")
RECALL_SCRIPT = _load_skill_script_module("recall.py")
build_query_route = cast(Callable[..., object], READ_ROUTER.build_query_route)
build_recall_route = cast(Callable[..., object], READ_ROUTER.build_recall_route)
route_read = cast(Callable[..., dict[str, object]], READ_ROUTER.route_read)


class _RouteWithCommand(Protocol):
    command: str


def test_fallback_cli_route_read_falls_back_to_cli_when_daemon_is_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cli_calls: list[dict[str, object]] = []

    def fake_cli(
        route: object, *, root: Path | None, snowiki_executable: str
    ) -> dict[str, object]:
        route_command = cast(_RouteWithCommand, route).command
        cli_calls.append(
            {
                "command": route_command,
                "root": root,
                "snowiki_executable": snowiki_executable,
            }
        )
        return {
            "ok": True,
            "command": "query",
            "result": {
                "query": "claude-basic",
                "mode": "lexical",
                "semantic_backend": None,
                "records_indexed": 4,
                "pages_indexed": 2,
                "hits": [],
            },
        }

    monkeypatch.setattr(READ_ROUTER, "_health", lambda host, port: None)
    monkeypatch.setattr(READ_ROUTER, "_run_cli_json", fake_cli)
    monkeypatch.setattr(
        READ_ROUTER,
        "daemon_request",
        lambda *_args, **_kwargs: pytest.fail(
            "daemon should not be called when offline"
        ),
    )

    payload = route_read(build_query_route("claude-basic"), root=tmp_path)

    assert payload == {
        "ok": True,
        "command": "query",
        "backend": "cli",
        "backend_diagnostics": {},
        "result": {
            "query": "claude-basic",
            "mode": "lexical",
            "semantic_backend": None,
            "records_indexed": 4,
            "pages_indexed": 2,
            "hits": [],
        },
    }
    assert cli_calls == [
        {
            "command": "query",
            "root": tmp_path,
            "snowiki_executable": "snowiki",
        }
    ]


def test_daemon_preferred_route_read_normalizes_daemon_payload_into_stable_cli_style_shape() -> (
    None
):
    daemon_calls: list[dict[str, object]] = []

    def fake_health(host: str, port: int) -> dict[str, object]:
        return {"ok": True, "host": host, "port": port}

    def fake_daemon_request(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        timeout: float = 1.0,
    ) -> dict[str, object]:
        daemon_calls.append(
            {
                "base_url": base_url,
                "path": path,
                "method": method,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return {
            "ok": True,
            "operation": "topical_recall",
            "query": "mixed language retrieval",
            "hits": [
                {
                    "path": "normalized/session-1.json",
                    "title": "Mixed language retrieval",
                    "kind": "session",
                    "score": 9.87654321,
                    "matched_terms": ["mixed", "language"],
                }
            ],
            "diagnostics": {
                "cache": {"kind": "ttl_response_cache"},
                "snapshot": {"snapshot_owner": "daemon.warm_indexes"},
            },
        }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(READ_ROUTER, "_health", fake_health)
    monkeypatch.setattr(READ_ROUTER, "daemon_request", fake_daemon_request)
    monkeypatch.setattr(
        READ_ROUTER,
        "_run_cli_json",
        lambda *_args, **_kwargs: pytest.fail("reachable daemon should be preferred"),
    )

    try:
        payload = route_read(build_query_route("mixed language retrieval", top_k=3))
    finally:
        monkeypatch.undo()

    assert payload == {
        "ok": True,
        "command": "query",
        "backend": "daemon",
        "backend_diagnostics": {
            "cache": {"kind": "ttl_response_cache"},
            "snapshot": {"snapshot_owner": "daemon.warm_indexes"},
        },
        "result": {
            "query": "mixed language retrieval",
            "mode": "lexical",
            "semantic_backend": None,
            "records_indexed": None,
            "pages_indexed": None,
            "hits": [
                {
                    "id": "normalized/session-1.json",
                    "path": "normalized/session-1.json",
                    "title": "Mixed language retrieval",
                    "kind": "session",
                    "source_type": "",
                    "score": 9.876543,
                    "matched_terms": ["mixed", "language"],
                    "summary": "",
                }
            ],
        },
    }
    assert daemon_calls == [
        {
            "base_url": "http://127.0.0.1:8765",
            "path": "/query",
            "method": "POST",
            "payload": {
                "operation": "topical_recall",
                "query": "mixed language retrieval",
                "limit": 3,
            },
            "timeout": 1.0,
        }
    ]


def test_daemon_path_preserves_query_and_recall_command_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "topical_recall": {
            "ok": True,
            "operation": "topical_recall",
            "query": "what do I know about BM25",
            "hits": [],
            "diagnostics": {},
        },
        "recall": {
            "ok": True,
            "operation": "recall",
            "query": "yesterday",
            "strategy": "temporal",
            "hits": [],
            "diagnostics": {},
        },
    }

    monkeypatch.setattr(READ_ROUTER, "_health", lambda host, port: {"ok": True})
    monkeypatch.setattr(
        READ_ROUTER,
        "daemon_request",
        lambda _base_url, _path, *, payload, **_kwargs: responses[payload["operation"]],
    )
    monkeypatch.setattr(
        READ_ROUTER,
        "_run_cli_json",
        lambda *_args, **_kwargs: pytest.fail(
            "daemon path should not use CLI fallback"
        ),
    )

    query_payload = route_read(build_query_route("what do I know about BM25"))
    recall_payload = route_read(build_recall_route("yesterday"))

    assert query_payload["command"] == "query"
    assert query_payload["result"] == {
        "query": "what do I know about BM25",
        "mode": "lexical",
        "semantic_backend": None,
        "records_indexed": None,
        "pages_indexed": None,
        "hits": [],
    }
    assert recall_payload["command"] == "recall"
    assert recall_payload["result"] == {
        "target": "yesterday",
        "strategy": "temporal",
        "hits": [],
    }


def test_query_script_uses_shared_router_as_thin_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    route_calls: list[dict[str, object]] = []

    def fake_route_read(
        route: object,
        *,
        root: Path | None,
        snowiki_executable: str,
        host: str,
        port: int,
        timeout: float,
    ) -> dict[str, object]:
        typed_route = cast(Any, route)
        route_calls.append(
            {
                "command": typed_route.command,
                "cli_args": typed_route.cli_args,
                "daemon_payload": typed_route.daemon_payload,
                "root": root,
                "snowiki_executable": snowiki_executable,
                "host": host,
                "port": port,
                "timeout": timeout,
            }
        )
        return {
            "ok": True,
            "command": "query",
            "backend": "daemon",
            "backend_diagnostics": {"cache": {"kind": "ttl_response_cache"}},
            "result": {"query": "bm25", "mode": "lexical", "hits": []},
        }

    monkeypatch.setattr(QUERY_SCRIPT, "route_read", fake_route_read)

    payload = QUERY_SCRIPT.run_query(
        "bm25",
        root=tmp_path,
        mode="lexical",
        top_k=7,
        host="127.0.0.1",
        port=9010,
        timeout=0.25,
    )

    assert payload["backend"] == "daemon"
    assert route_calls == [
        {
            "command": "query",
            "cli_args": ("query", "bm25", "--mode", "lexical", "--top-k", "7"),
            "daemon_payload": {
                "operation": "topical_recall",
                "query": "bm25",
                "limit": 7,
            },
            "root": tmp_path,
            "snowiki_executable": "snowiki",
            "host": "127.0.0.1",
            "port": 9010,
            "timeout": 0.25,
        }
    ]


def test_recall_script_uses_shared_router_as_thin_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    route_calls: list[dict[str, object]] = []

    def fake_route_read(
        route: object,
        *,
        root: Path | None,
        snowiki_executable: str,
        host: str,
        port: int,
        timeout: float,
    ) -> dict[str, object]:
        typed_route = cast(Any, route)
        route_calls.append(
            {
                "command": typed_route.command,
                "cli_args": typed_route.cli_args,
                "daemon_payload": typed_route.daemon_payload,
                "root": root,
                "snowiki_executable": snowiki_executable,
                "host": host,
                "port": port,
                "timeout": timeout,
            }
        )
        return {
            "ok": True,
            "command": "recall",
            "backend": "cli",
            "backend_diagnostics": {},
            "result": {"target": "yesterday", "strategy": "temporal", "hits": []},
        }

    monkeypatch.setattr(RECALL_SCRIPT, "route_read", fake_route_read)

    payload = RECALL_SCRIPT.run_recall(
        "yesterday",
        root=tmp_path,
        host="127.0.0.1",
        port=9011,
        timeout=0.5,
    )

    assert payload["backend"] == "cli"
    assert route_calls == [
        {
            "command": "recall",
            "cli_args": ("recall", "yesterday"),
            "daemon_payload": {
                "operation": "recall",
                "query": "yesterday",
                "limit": 10,
            },
            "root": tmp_path,
            "snowiki_executable": "snowiki",
            "host": "127.0.0.1",
            "port": 9011,
            "timeout": 0.5,
        }
    ]
