from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ToolSpec, coerce_limit, coerce_query

if TYPE_CHECKING:
    from ..server import SnowikiReadOnlyFacade


def build_tool(facade: SnowikiReadOnlyFacade) -> ToolSpec:
    """Build the read-only search MCP tool."""

    def handler(arguments: dict[str, object]) -> dict[str, object]:
        return facade.search(
            coerce_query(arguments), limit=coerce_limit(arguments.get("limit"))
        )

    return ToolSpec(
        name="search",
        description="Search session and compiled page content without modifying storage.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query string to search for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of hits to return.",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["query"],
        },
        handler=handler,
    )
