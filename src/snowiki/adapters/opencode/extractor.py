from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .parser import RawPart


@dataclass(frozen=True, slots=True)
class ExtractedPart:
    type: str
    text: str | None
    data: dict[str, Any] | None
    mime_type: str | None = None


def _tool_text(payload: dict[str, Any]) -> str | None:
    state = payload.get("state")
    if not isinstance(state, dict):
        return None
    output = state.get("output")
    if isinstance(output, str):
        return output
    metadata = state.get("metadata")
    if isinstance(metadata, dict):
        maybe_output = metadata.get("output")
        if isinstance(maybe_output, str):
            return maybe_output
    return None


def extract_part_payload(raw_part: RawPart) -> ExtractedPart:
    payload = dict(raw_part.data)
    part_type = str(payload.get("type", "unknown"))

    if part_type == "text":
        text = payload.get("text")
        return ExtractedPart(
            type="text", text=text if isinstance(text, str) else "", data=payload
        )

    if part_type == "reasoning":
        text = payload.get("text")
        return ExtractedPart(
            type="reasoning",
            text=text if isinstance(text, str) else None,
            data=payload,
        )

    if part_type == "tool":
        return ExtractedPart(type="tool", text=_tool_text(payload), data=payload)

    if part_type == "patch":
        return ExtractedPart(
            type="patch", text=None, data=payload, mime_type="text/x-diff"
        )

    if part_type == "agent":
        return ExtractedPart(type="agent", text=None, data=payload)

    if part_type == "compaction":
        return ExtractedPart(type="compaction", text=None, data=payload)

    return ExtractedPart(
        type=part_type,
        text=payload.get("text") if isinstance(payload.get("text"), str) else None,
        data=payload,
    )


__all__ = ["ExtractedPart", "extract_part_payload"]
