from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

type MCPObject = dict[str, object]
type MCPMapping = Mapping[str, object]


@dataclass(frozen=True)
class ToolSpec:
    """Description of an exposed MCP tool."""

    name: str
    description: str
    input_schema: MCPObject
    handler: Callable[[MCPObject], MCPObject]


@dataclass(frozen=True)
class ResourceSpec:
    """Description of an exposed MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


class ReadOnlyFacade(Protocol):
    """Protocol for the read-only Snowiki MCP facade."""

    def search(self, query: str, *, limit: int = 5) -> MCPObject: ...

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        mode: str = "auto",
        reference_time: datetime | None = None,
    ) -> MCPObject: ...

    def get_page(self, path: str) -> MCPObject: ...

    def resolve_links(self, path: str) -> MCPObject: ...

    def graph_resource(self) -> MCPObject: ...

    def topic_resource(self, topic_slug: str) -> MCPObject: ...

    def session_resource(self, session_id: str) -> MCPObject: ...

    def list_resources(self) -> list[ResourceSpec]: ...

    def read_resource(self, uri: str) -> MCPObject: ...


def coerce_limit(value: object, *, default: int = 5) -> int:
    if value is None:
        return default
    if not isinstance(value, int | str):
        raise ValueError("`limit` must be an integer.")
    limit = int(value)
    if limit < 1:
        return 1
    return min(limit, 50)


def coerce_query(arguments: MCPMapping) -> str:
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("`query` must be a non-empty string.")
    return query.strip()


def coerce_path(arguments: MCPMapping) -> str:
    path = arguments.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("`path` must be a non-empty string.")
    return path.strip()
