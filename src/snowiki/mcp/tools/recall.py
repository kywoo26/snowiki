from __future__ import annotations

from datetime import datetime

from ..types import ReadOnlyFacade, ToolSpec, coerce_limit, coerce_query


def build_tool(facade: ReadOnlyFacade) -> ToolSpec:
    """Build the read-only recall MCP tool."""

    def handler(arguments: dict[str, object]) -> dict[str, object]:
        reference_time = arguments.get("reference_time")
        parsed_reference_time: datetime | None = None
        if isinstance(reference_time, str) and reference_time.strip():
            parsed_reference_time = datetime.fromisoformat(
                reference_time.replace("Z", "+00:00")
            )
        mode = arguments.get("mode")
        if not isinstance(mode, str) or not mode.strip():
            mode = "auto"
        return facade.recall(
            coerce_query(arguments),
            limit=coerce_limit(arguments.get("limit")),
            mode=mode,
            reference_time=parsed_reference_time,
        )

    return ToolSpec(
        name="recall",
        description="Recall knowledge using CLI-truth auto-routing across date, temporal, known-item, and topic strategies.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Recall query."},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of hits.",
                    "minimum": 1,
                    "maximum": 50,
                },
                "mode": {
                    "type": "string",
                    "description": "Recall mode: auto, date, temporal, known_item, or topic.",
                },
                "reference_time": {
                    "type": "string",
                    "description": "Optional ISO-8601 time used for temporal recall.",
                },
            },
            "required": ["query"],
        },
        handler=handler,
    )
