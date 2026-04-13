from __future__ import annotations

from ..types import ReadOnlyFacade, ToolSpec, coerce_path


def build_tool(facade: ReadOnlyFacade) -> ToolSpec:
    """Build the read-only get-page MCP tool."""

    def handler(arguments: dict[str, object]) -> dict[str, object]:
        return facade.get_page(coerce_path(arguments))

    return ToolSpec(
        name="get_page",
        description="Fetch a compiled page by path without editing it.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Compiled page path."},
            },
            "required": ["path"],
        },
        handler=handler,
    )
