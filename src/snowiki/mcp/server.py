from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import cast
from urllib.parse import unquote, urlparse

from snowiki.schema.compiled import slugify
from snowiki.search import (
    known_item_lookup,
    run_authoritative_recall,
    temporal_recall,
    topical_recall,
)
from snowiki.search.contract import RecallMode
from snowiki.search.models import SearchHit
from snowiki.search.requests import RuntimeSearchRequest
from snowiki.search.runtime_service import RetrievalService

from .types import MCPMapping, MCPObject, ResourceSpec

WRITE_OPERATION_NAMES = frozenset(
    {"edit", "ingest", "merge", "status", "sync", "write"}
)
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)")


def serialize_hit(hit: SearchHit) -> MCPObject:
    document = hit.document
    return {
        "id": document.id,
        "kind": document.kind,
        "matched_terms": list(hit.matched_terms),
        "metadata": dict(document.metadata),
        "path": document.path,
        "recorded_at": document.recorded_at.isoformat()
        if document.recorded_at
        else None,
        "score": hit.score,
        "source_type": document.source_type,
        "summary": document.summary,
        "title": document.title,
    }


class SnowikiReadOnlyFacade:
    """Read-only facade used by the MCP server and tools."""

    def __init__(
        self,
        *,
        session_records: Sequence[MCPMapping] = (),
        compiled_pages: Sequence[MCPMapping] = (),
        reference_time: datetime | None = None,
    ) -> None:
        self.session_records = tuple(dict(record) for record in session_records)
        self.compiled_pages = tuple(dict(page) for page in compiled_pages)
        self.reference_time = reference_time or datetime.now(tz=UTC)

        snapshot = RetrievalService.from_records_and_pages(
            records=list(self.session_records),
            pages=list(self.compiled_pages),
        )
        self.index = snapshot.index

        self.page_by_path = {
            str(page.get("path", "")).strip(): dict(page)
            for page in self.compiled_pages
            if str(page.get("path", "")).strip()
        }
        self.page_path_by_slug = {
            self.page_slug(page): path for path, page in self.page_by_path.items()
        }
        self.page_path_by_title = {
            str(page.get("title", "")).strip().casefold(): path
            for path, page in self.page_by_path.items()
            if str(page.get("title", "")).strip()
        }
        self.session_by_id = {
            str(record.get("id", "")).strip(): dict(record)
            for record in self.session_records
            if str(record.get("id", "")).strip()
        }
        self.session_by_path = {
            str(record.get("path", "")).strip(): dict(record)
            for record in self.session_records
            if str(record.get("path", "")).strip()
        }

    def search(self, query: str, *, limit: int = 5) -> MCPObject:
        """Search normalized sessions and compiled pages."""
        hits = self.index.search(
            RuntimeSearchRequest(query=query, candidate_limit=limit)
        )
        return {
            "hits": [serialize_hit(hit) for hit in hits],
            "limit": limit,
            "query": query,
        }

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        mode: str = "auto",
        reference_time: datetime | None = None,
    ) -> MCPObject:
        """Recall topical or temporal knowledge from the runtime index."""
        normalized_mode = self._normalize_recall_mode(mode)
        hits, strategy = run_authoritative_recall(
            self.index,
            query,
            limit=limit,
            known_item_lookup=known_item_lookup,
            temporal_recall=temporal_recall,
            topical_recall=topical_recall,
            mode=normalized_mode,
            reference_time=reference_time or self.reference_time,
        )
        return {
            "hits": [serialize_hit(hit) for hit in hits],
            "limit": limit,
            "mode": strategy,
            "query": query,
            "strategy": strategy,
        }

    def get_page(self, path: str) -> MCPObject:
        """Return a compiled page by its storage path."""
        page = self.page_by_path.get(path)
        if page is None:
            raise KeyError(f"Unknown page path: {path}")
        return dict(page)

    def resolve_links(self, path: str) -> MCPObject:
        """Resolve related links and wikilinks for a compiled page."""
        page = self.get_page(path)
        body = str(page.get("body") or page.get("content") or "")
        wikilinks = []
        seen_targets: set[str] = set()

        related_targets = page.get("related")
        for target in related_targets if isinstance(related_targets, list) else []:
            if not isinstance(target, str) or not target.strip():
                continue
            normalized_target = target.strip()
            if normalized_target in seen_targets:
                continue
            seen_targets.add(normalized_target)
            wikilinks.append(self._resolved_link(normalized_target))

        for match in WIKILINK_PATTERN.findall(body):
            target = match.strip()
            if not target or target in seen_targets:
                continue
            seen_targets.add(target)
            wikilinks.append(self._resolved_link(target))

        return {"links": wikilinks, "path": path}

    def list_resources(self) -> list[ResourceSpec]:
        """List graph, topic, and session resources exposed by the server."""
        resources = [
            ResourceSpec(
                uri="graph://current",
                name="graph",
                description="Current read-only wiki graph.",
            )
        ]
        for page in self.compiled_pages:
            page_path = str(page.get("path", "")).strip()
            if not page_path:
                continue
            resources.append(
                ResourceSpec(
                    uri=f"topic://{self.page_slug(page)}",
                    name=str(page.get("title") or page_path),
                    description=f"Compiled topic page {page_path}",
                )
            )
        for record in self.session_records:
            session_id = str(record.get("id", "")).strip()
            if not session_id:
                continue
            resources.append(
                ResourceSpec(
                    uri=f"session://{session_id}",
                    name=str(record.get("title") or session_id),
                    description=f"Session record {session_id}",
                )
            )
        resources.sort(key=lambda resource: (resource.uri, resource.name))
        return resources

    def read_resource(self, uri: str) -> MCPObject:
        """Read a graph, topic, or session resource by URI."""
        parsed = urlparse(uri)
        if parsed.scheme == "graph":
            return self.graph_resource()
        if parsed.scheme == "topic":
            return self.topic_resource(unquote(parsed.netloc or parsed.path))
        if parsed.scheme == "session":
            return self.session_resource(unquote(parsed.netloc or parsed.path))
        raise KeyError(f"Unknown resource URI: {uri}")

    def graph_resource(self) -> MCPObject:
        """Return the current read-only graph resource."""
        nodes: list[MCPObject] = []
        edges: list[dict[str, str]] = []
        for page in self.compiled_pages:
            page_path = str(page.get("path", "")).strip()
            if not page_path:
                continue
            nodes.append(
                {
                    "id": page_path,
                    "kind": "page",
                    "title": str(page.get("title") or page_path),
                }
            )
            related_values = page.get("related")
            for related in related_values if isinstance(related_values, list) else []:
                if isinstance(related, str) and related.strip():
                    edges.append({"source": page_path, "target": related.strip()})

        for record in self.session_records:
            session_path = str(record.get("path") or record.get("id") or "").strip()
            if not session_path:
                continue
            nodes.append(
                {
                    "id": session_path,
                    "kind": "session",
                    "title": str(record.get("title") or session_path),
                }
            )

        nodes.sort(key=lambda node: (str(node["kind"]), str(node["id"])))
        edges.sort(key=lambda edge: (edge["source"], edge["target"]))
        return {"edges": edges, "nodes": nodes}

    def topic_resource(self, topic_slug: str) -> MCPObject:
        """Return summary metadata for a compiled topic page."""
        topic_key = topic_slug.strip().strip("/")
        if not topic_key:
            raise KeyError("Topic resource requires a slug.")
        page_path = self.page_path_by_slug.get(topic_key)
        if page_path is None:
            raise KeyError(f"Unknown topic resource: {topic_slug}")
        page = self.get_page(page_path)
        return {
            "path": page_path,
            "slug": topic_key,
            "summary": str(page.get("summary") or ""),
            "title": str(page.get("title") or page_path),
        }

    def session_resource(self, session_id: str) -> MCPObject:
        """Return a normalized session payload by id or path."""
        key = session_id.strip().strip("/")
        if not key:
            raise KeyError("Session resource requires a session id.")
        session = self.session_by_id.get(key) or self.session_by_path.get(key)
        if session is None:
            raise KeyError(f"Unknown session resource: {session_id}")
        return dict(session)

    def page_slug(self, page: MCPMapping) -> str:
        """Build a stable slug for a compiled page mapping."""
        path = str(page.get("path", "")).strip()
        if path:
            return slugify(PurePosixPath(path).stem)
        title = str(page.get("title", "")).strip()
        return slugify(title or "page")

    def _normalize_recall_mode(self, mode: str) -> RecallMode:
        selected_mode = mode.strip().lower()
        if selected_mode == "topical":
            selected_mode = "topic"
        if selected_mode not in {"auto", "date", "temporal", "known_item", "topic"}:
            raise ValueError(
                "`mode` must be one of: auto, date, temporal, known_item, topic."
            )
        return cast(RecallMode, selected_mode)

    def _resolved_link(self, target: str) -> MCPObject:
        cleaned = target.strip()
        resolved_path = self.page_by_path.get(cleaned)
        if resolved_path is not None:
            path = cleaned
        else:
            path = self.page_path_by_slug.get(slugify(cleaned))
            if path is None:
                path = self.page_path_by_title.get(cleaned.casefold())
        return {
            "target": cleaned,
            "resolved_path": path,
            "resolved": path is not None,
        }


class ReadOnlyMCPServer:
    """JSON-RPC server wrapper around the read-only Snowiki facade."""

    def __init__(self, facade: SnowikiReadOnlyFacade) -> None:
        self.facade = facade
        from .tools.get_page import build_tool as build_get_page_tool
        from .tools.recall import build_tool as build_recall_tool
        from .tools.resolve_links import build_tool as build_resolve_links_tool
        from .tools.search import build_tool as build_search_tool

        self.tool_map = {
            tool.name: tool
            for tool in (
                build_search_tool(facade),
                build_recall_tool(facade),
                build_get_page_tool(facade),
                build_resolve_links_tool(facade),
            )
        }

    def list_tools(self) -> list[MCPObject]:
        """List MCP tool metadata in protocol response format."""
        tools = []
        for tool in sorted(self.tool_map.values(), key=lambda item: item.name):
            tools.append(
                {
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                    "name": tool.name,
                }
            )
        return tools

    def list_resources(self) -> list[MCPObject]:
        """List MCP resources in protocol response format."""
        return [
            {
                "description": resource.description,
                "mimeType": resource.mime_type,
                "name": resource.name,
                "uri": resource.uri,
            }
            for resource in self.facade.list_resources()
        ]

    def call_tool(self, name: str, arguments: MCPObject) -> MCPObject:
        """Dispatch an MCP tool call and serialize the structured response."""
        if name in WRITE_OPERATION_NAMES:
            return self._tool_error(
                f"Write operation `{name}` is not exposed by this read-only MCP facade."
            )
        tool = self.tool_map.get(name)
        if tool is None:
            return self._tool_error(f"Unknown tool `{name}`.")
        try:
            structured = tool.handler(arguments)
        except (KeyError, ValueError) as error:
            return self._tool_error(str(error))
        return {
            "content": [
                {
                    "text": json.dumps(structured, ensure_ascii=False, sort_keys=True),
                    "type": "text",
                }
            ],
            "structuredContent": structured,
        }

    def read_resource(self, uri: str) -> MCPObject:
        """Read a resource and format it as an MCP response payload."""
        try:
            structured = self.facade.read_resource(uri)
        except KeyError as error:
            return self._resource_error(uri, str(error))
        return {
            "contents": [
                {
                    "mimeType": "application/json",
                    "text": json.dumps(structured, ensure_ascii=False, sort_keys=True),
                    "uri": uri,
                }
            ]
        }

    def handle_message(self, message: MCPMapping) -> MCPObject | None:
        """Handle a single MCP JSON-RPC request message."""
        method = message.get("method")
        if not isinstance(method, str):
            return self._error_response(
                message.get("id"), code=-32600, text="Invalid request."
            )

        if "id" not in message and method == "notifications/initialized":
            return None

        params = message.get("params")
        if isinstance(params, dict):
            params_map = {str(key): value for key, value in params.items()}
        else:
            params_map: dict[str, object] = {}

        if method == "initialize":
            return self._success_response(
                message.get("id"),
                {
                    "capabilities": {
                        "resources": {"listChanged": False, "subscribe": False},
                        "tools": {"listChanged": False},
                    },
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {"name": "snowiki-readonly", "version": "0.1.0"},
                },
            )
        if method == "tools/list":
            return self._success_response(
                message.get("id"), {"tools": self.list_tools()}
            )
        if method == "tools/call":
            name = params_map.get("name")
            if not isinstance(name, str):
                return self._error_response(
                    message.get("id"), code=-32602, text="Tool name is required."
                )
            arguments = params_map.get("arguments")
            if isinstance(arguments, dict):
                argument_map = {str(key): value for key, value in arguments.items()}
            else:
                argument_map: MCPObject = {}
            return self._success_response(
                message.get("id"), self.call_tool(name, argument_map)
            )
        if method == "resources/list":
            return self._success_response(
                message.get("id"), {"resources": self.list_resources()}
            )
        if method == "resources/read":
            uri = params_map.get("uri")
            if not isinstance(uri, str):
                return self._error_response(
                    message.get("id"), code=-32602, text="Resource URI is required."
                )
            return self._success_response(message.get("id"), self.read_resource(uri))
        return self._error_response(
            message.get("id"), code=-32601, text=f"Method not found: {method}"
        )

    def _error_response(self, request_id: object, *, code: int, text: str) -> MCPObject:
        return {
            "error": {"code": code, "message": text},
            "id": request_id,
            "jsonrpc": "2.0",
        }

    def _resource_error(self, uri: str, message: str) -> MCPObject:
        return {
            "contents": [
                {
                    "mimeType": "application/json",
                    "text": json.dumps(
                        {"error": message, "uri": uri},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "uri": uri,
                }
            ]
        }

    def _success_response(self, request_id: object, result: MCPObject) -> MCPObject:
        return {"id": request_id, "jsonrpc": "2.0", "result": result}

    def _tool_error(self, message: str) -> MCPObject:
        return {
            "content": [{"text": message, "type": "text"}],
            "isError": True,
            "structuredContent": {"error": message},
        }


def create_server(
    *,
    session_records: Sequence[MCPMapping] = (),
    compiled_pages: Sequence[MCPMapping] = (),
    reference_time: datetime | None = None,
) -> ReadOnlyMCPServer:
    """Create a read-only Snowiki MCP server instance."""
    facade = SnowikiReadOnlyFacade(
        session_records=session_records,
        compiled_pages=compiled_pages,
        reference_time=reference_time,
    )
    return ReadOnlyMCPServer(facade)
