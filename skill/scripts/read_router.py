from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from snowiki.cli.commands.daemon import DEFAULT_HOST, DEFAULT_PORT, _base_url, _health
from snowiki.daemon.fallback import daemon_request, execute_with_fallback

ReadCommand = Literal["query", "recall"]


@dataclass(frozen=True, slots=True)
class WikiReadRoute:
    """Normalized transport request for a read-only wiki command.

    Attributes:
        command: Canonical command identity exposed by the skill surface.
        cli_args: Positional CLI arguments excluding shared JSON/root flags.
        daemon_payload: POST payload used for the daemon /query endpoint.
        daemon_result: Command-specific metadata needed to normalize daemon output.
    """

    command: ReadCommand
    cli_args: tuple[str, ...]
    daemon_payload: dict[str, Any]
    daemon_result: dict[str, Any]


def build_query_route(
    query: str,
    *,
    mode: str = "lexical",
    top_k: int = 5,
) -> WikiReadRoute:
    """Build a router request for direct lexical query semantics."""
    return WikiReadRoute(
        command="query",
        cli_args=("query", query, "--mode", mode, "--top-k", str(top_k)),
        daemon_payload={"operation": "topical_recall", "query": query, "limit": top_k},
        daemon_result={"query": query, "mode": mode, "top_k": top_k},
    )


def build_recall_route(target: str) -> WikiReadRoute:
    """Build a router request for authoritative recall semantics."""
    return WikiReadRoute(
        command="recall",
        cli_args=("recall", target),
        daemon_payload={"operation": "recall", "query": target, "limit": 10},
        daemon_result={"target": target},
    )


def route_read(
    route: WikiReadRoute,
    *,
    root: Path | None = None,
    snowiki_executable: str = "snowiki",
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 1.0,
) -> dict[str, Any]:
    """Route a read request to a reachable daemon or the canonical CLI.

    The daemon is used only when already reachable. If the daemon becomes
    unavailable after a positive health probe, the call still falls back to the
    canonical CLI JSON surface.
    """

    if _health(host, port) is None:
        return _normalize_cli_payload(
            _run_cli_json(route, root=root, snowiki_executable=snowiki_executable),
            command=route.command,
        )

    selected = execute_with_fallback(
        lambda: _run_daemon_json(route, host=host, port=port, timeout=timeout),
        lambda: _run_cli_json(route, root=root, snowiki_executable=snowiki_executable),
    )
    if selected["mode"] == "daemon":
        return _normalize_daemon_payload(
            route,
            _expect_mapping(selected["result"], context="daemon result"),
        )
    return _normalize_cli_payload(
        _expect_mapping(selected["result"], context="cli result"),
        command=route.command,
    )


def _run_daemon_json(
    route: WikiReadRoute, *, host: str, port: int, timeout: float
) -> dict[str, Any]:
    return daemon_request(
        _base_url(host, port),
        "/query",
        method="POST",
        payload=route.daemon_payload,
        timeout=timeout,
    )


def _run_cli_json(
    route: WikiReadRoute,
    *,
    root: Path | None,
    snowiki_executable: str,
) -> dict[str, Any]:
    command = [snowiki_executable, *route.cli_args]
    if root is not None:
        command.extend(["--root", str(root)])
    command.extend(["--output", "json"])
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = completed.stdout.strip()
    if not output:
        stderr = completed.stderr.strip()
        raise RuntimeError(stderr or "snowiki command produced no JSON output")
    try:
        decoded = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("snowiki command returned invalid JSON output") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("snowiki command returned unsupported JSON payload")
    return decoded


def _normalize_cli_payload(
    payload: dict[str, Any], *, command: ReadCommand
) -> dict[str, Any]:
    normalized = {
        "ok": bool(payload.get("ok", False)),
        "command": str(payload.get("command") or command),
        "backend": "cli",
        "backend_diagnostics": {},
    }
    if normalized["ok"]:
        normalized["result"] = _expect_mapping(
            payload.get("result"), context="cli payload"
        )
        return normalized
    if "error" in payload:
        normalized["error"] = _expect_mapping(payload.get("error"), context="cli error")
        return normalized
    normalized["error"] = {"code": "error", "message": "CLI read failed."}
    return normalized


def _normalize_daemon_payload(
    route: WikiReadRoute, payload: dict[str, Any]
) -> dict[str, Any]:
    diagnostics = payload.get("diagnostics")
    normalized = {
        "ok": bool(payload.get("ok", False)),
        "command": route.command,
        "backend": "daemon",
        "backend_diagnostics": (
            _expect_mapping(diagnostics, context="daemon diagnostics")
            if isinstance(diagnostics, dict)
            else {}
        ),
    }
    if not normalized["ok"]:
        message = str(payload.get("error") or "Daemon read failed.")
        normalized["error"] = {"code": "daemon_error", "message": message}
        return normalized
    normalized["result"] = _normalize_daemon_result(route, payload)
    return normalized


def _normalize_daemon_result(
    route: WikiReadRoute, payload: dict[str, Any]
) -> dict[str, Any]:
    if route.command == "query":
        return {
            "query": str(payload.get("query") or route.daemon_result["query"]),
            "mode": str(route.daemon_result["mode"]),
            "semantic_backend": (
                "disabled" if route.daemon_result["mode"] == "hybrid" else None
            ),
            "records_indexed": None,
            "pages_indexed": None,
            "hits": _normalize_query_hits(payload.get("hits")),
        }
    return {
        "target": str(payload.get("query") or route.daemon_result["target"]),
        "strategy": str(payload.get("strategy") or "topic"),
        "hits": _normalize_recall_hits(payload.get("hits")),
    }


def _normalize_query_hits(raw_hits: object) -> list[dict[str, Any]]:
    hits = _coerce_hits(raw_hits)
    return [
        {
            "id": str(hit.get("id") or hit.get("path") or ""),
            "path": str(hit.get("path") or hit.get("id") or ""),
            "title": str(hit.get("title") or hit.get("path") or hit.get("id") or ""),
            "kind": str(hit.get("kind") or ""),
            "source_type": str(hit.get("source_type") or ""),
            "score": _round_score(hit.get("score")),
            "matched_terms": _normalize_matched_terms(hit.get("matched_terms")),
            "summary": str(hit.get("summary") or ""),
        }
        for hit in hits
    ]


def _normalize_recall_hits(raw_hits: object) -> list[dict[str, Any]]:
    hits = _coerce_hits(raw_hits)
    return [
        {
            "id": str(hit.get("id") or hit.get("path") or ""),
            "path": str(hit.get("path") or hit.get("id") or ""),
            "title": str(hit.get("title") or hit.get("path") or hit.get("id") or ""),
            "kind": str(hit.get("kind") or ""),
            "score": _round_score(hit.get("score")),
            "summary": str(hit.get("summary") or ""),
        }
        for hit in hits
    ]


def _coerce_hits(raw_hits: object) -> list[dict[str, Any]]:
    if not isinstance(raw_hits, list):
        return []
    hits: list[dict[str, Any]] = []
    for hit in raw_hits:
        if isinstance(hit, Mapping):
            hits.append(dict(cast(Mapping[str, Any], hit)))
    return hits


def _normalize_matched_terms(raw_terms: object) -> list[str]:
    if not isinstance(raw_terms, list):
        return []
    return [str(term) for term in raw_terms if isinstance(term, str | int | float)]


def _round_score(raw_score: object) -> float:
    if not isinstance(raw_score, int | float):
        return 0.0
    return round(float(raw_score), 6)


def _expect_mapping(value: object, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} must be a JSON object")
    return cast(dict[str, Any], value)
