from __future__ import annotations

from ..types import ReadOnlyFacade, ToolSpec, coerce_limit, coerce_query


def build_tool(facade: ReadOnlyFacade) -> ToolSpec:
    """Build the read-only search MCP tool."""

    def handler(arguments: dict[str, object]) -> dict[str, object]:
        return facade.search(
            coerce_query(arguments), limit=coerce_limit(arguments.get("limit"))
        )

    return ToolSpec(
        name="search",
        description="Search session and compiled page content directly without recall auto-routing or storage mutation.",
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
