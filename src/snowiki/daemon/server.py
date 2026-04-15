from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib import parse

from snowiki.search import (
    known_item_lookup,
    run_authoritative_recall,
    temporal_recall,
    topical_recall,
)

from .cache import TTLQueryCache
from .invalidation import CacheInvalidationManager, InvalidationEvent
from .lifecycle import DaemonLifecycle
from .warm_index import WarmIndexManager, WarmSnapshotStaleError


@dataclass(frozen=True, slots=True)
class QueryRequest:
    operation: str
    query: str
    limit: int = 10


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class SnowikiDaemon:
    def __init__(
        self,
        root: str | Path,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        cache_ttl_seconds: float = 30.0,
        state_file: str | Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.host = host
        self.port = port
        self.warm_indexes = WarmIndexManager(self.root)
        self.cache = TTLQueryCache(ttl_seconds=cache_ttl_seconds)
        self.invalidator = CacheInvalidationManager(self.warm_indexes, self.cache)
        self.state_file = Path(state_file or self.root / "index" / "daemon-state.json")
        self._server = _ThreadingHTTPServer(
            (self.host, self.port), self._build_handler()
        )
        self.lifecycle = DaemonLifecycle(
            server=self._server,
            warm_indexes=self.warm_indexes,
            cache=self.cache,
            host=self.host,
            port=self.port,
            state_file=self.state_file,
        )

    def serve_forever(self) -> None:
        self.warm_indexes.get()
        self.lifecycle.mark_started()
        try:
            self._server.serve_forever()
        finally:
            self.lifecycle.mark_stopped()
            self._server.server_close()

    def execute_query(self, request_model: QueryRequest) -> dict[str, Any]:
        try:
            fresh_snapshot = self.warm_indexes.ensure_fresh_snapshot()
        except WarmSnapshotStaleError:
            self.cache.invalidate()
            raise
        if fresh_snapshot.reloaded:
            self.cache.invalidate()
        cache_key = json.dumps(asdict(request_model), sort_keys=True)
        return self.cache.get_or_set(
            cache_key,
            lambda: self._run_query(request_model, fresh_snapshot.snapshot),
        )

    def invalidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = InvalidationEvent(
            kind=str(payload.get("event") or "rebuild"),
            reason=str(payload.get("reason") or ""),
            payload=dict(payload),
        )
        return self.invalidator.handle(event)

    def _run_query(
        self, request_model: QueryRequest, snapshot: Any | None = None
    ) -> dict[str, Any]:
        current_snapshot = snapshot or self.warm_indexes.get()
        operations: dict[str, Callable[..., Any]] = {
            "known_item_lookup": known_item_lookup,
            "topical_recall": topical_recall,
            "temporal_recall": temporal_recall,
        }
        strategy: str | None = None
        if request_model.operation == "recall":
            hits, strategy = self._run_recall(current_snapshot.blended, request_model)
        else:
            handler = operations.get(request_model.operation)
            if handler is None:
                raise ValueError(f"unsupported operation: {request_model.operation}")

            hits = handler(
                current_snapshot.blended, request_model.query, limit=request_model.limit
            )
            strategy = request_model.operation
        return {
            "ok": True,
            "cached": False,
            "operation": request_model.operation,
            "query": request_model.query,
            "limit": request_model.limit,
            "strategy": strategy,
            "diagnostics": {
                "snapshot": self.warm_indexes.snapshot_metadata(current_snapshot),
                "cache": {
                    "owner": "daemon.response_cache",
                    "kind": "ttl_response_cache",
                    "ttl_seconds": self.cache.ttl_seconds,
                },
            },
            "hits": [
                {
                    "path": hit.document.path,
                    "title": hit.document.title,
                    "kind": hit.document.kind,
                    "score": hit.score,
                    "matched_terms": list(hit.matched_terms),
                }
                for hit in hits
            ],
        }

    def _run_recall(
        self, index: Any, request_model: QueryRequest
    ) -> tuple[list[Any], str]:
        return run_authoritative_recall(
            index,
            request_model.query,
            limit=request_model.limit,
            known_item_lookup=known_item_lookup,
            temporal_recall=temporal_recall,
            topical_recall=topical_recall,
        )

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        daemon = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = parse.urlparse(self.path)
                if parsed.path == "/health":
                    self._send_json(200, daemon.lifecycle.health_payload())
                    return
                if parsed.path == "/status":
                    self._send_json(200, daemon.lifecycle.status_payload())
                    return
                self._send_json(404, {"ok": False, "error": "not found"})

            def do_POST(self) -> None:
                parsed = parse.urlparse(self.path)
                payload = self._read_json_body()
                if parsed.path == "/query":
                    try:
                        request_model = QueryRequest(
                            operation=str(
                                payload.get("operation") or "known_item_lookup"
                            ),
                            query=str(payload.get("query") or ""),
                            limit=max(1, int(payload.get("limit") or 10)),
                        )
                        response = daemon.execute_query(request_model)
                    except WarmSnapshotStaleError as exc:
                        self._send_json(
                            503,
                            {
                                "ok": False,
                                "error": str(exc),
                                "diagnostics": {
                                    "snapshot": exc.freshness,
                                    "cache": {
                                        "owner": "daemon.response_cache",
                                        "kind": "ttl_response_cache",
                                        "ttl_seconds": daemon.cache.ttl_seconds,
                                    },
                                },
                            },
                        )
                        return
                    except ValueError as exc:
                        self._send_json(400, {"ok": False, "error": str(exc)})
                        return
                    self._send_json(200, response)
                    return

                if parsed.path == "/invalidate":
                    self._send_json(200, daemon.invalidate(payload))
                    return

                if parsed.path in {"/stop", "/shutdown"}:
                    payload = daemon.lifecycle.stop_payload()
                    self._send_json(200, payload)
                    daemon.lifecycle.begin_shutdown()
                    return

                self._send_json(404, {"ok": False, "error": "not found"})

            def log_message(self, format: str, *args: object) -> None:
                return

            def _read_json_body(self) -> dict[str, Any]:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                if content_length <= 0:
                    return {}
                raw = self.rfile.read(content_length).decode("utf-8")
                try:
                    decoded = json.loads(raw)
                except json.JSONDecodeError:
                    return {}
                return decoded if isinstance(decoded, dict) else {}

            def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                self.wfile.flush()

        return Handler


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="snowiki-daemon")
    parser.add_argument("--root", default=".", help="Snowiki storage root")
    parser.add_argument("--host", default="127.0.0.1", help="Daemon bind host")
    parser.add_argument("--port", type=int, default=8765, help="Daemon bind port")
    parser.add_argument(
        "--cache-ttl",
        type=float,
        default=30.0,
        help="Query cache TTL in seconds",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Path for daemon state metadata",
    )
    return parser


def run_daemon(args: argparse.Namespace | None = None) -> SnowikiDaemon:
    parser = build_argument_parser()
    namespace = args or parser.parse_args()
    daemon = SnowikiDaemon(
        root=namespace.root,
        host=namespace.host,
        port=namespace.port,
        cache_ttl_seconds=namespace.cache_ttl,
        state_file=namespace.state_file,
    )
    daemon.serve_forever()
    return daemon


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    run_daemon(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
