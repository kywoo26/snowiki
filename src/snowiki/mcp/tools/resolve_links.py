from __future__ import annotations

from ..types import ReadOnlyFacade, ToolSpec, coerce_path


def build_tool(facade: ReadOnlyFacade) -> ToolSpec:
    """Build the read-only resolve-links MCP tool."""

    def handler(arguments: dict[str, object]) -> dict[str, object]:
        return facade.resolve_links(coerce_path(arguments))

    return ToolSpec(
        name="resolve_links",
        description="Resolve wikilinks and related links for a compiled page.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Compiled page path to inspect.",
                },
            },
            "required": ["path"],
        },
        handler=handler,
    )
