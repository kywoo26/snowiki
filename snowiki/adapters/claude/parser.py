from __future__ import annotations

import json
from pathlib import Path

type ClaudeScalar = None | bool | int | float | str
type ClaudeValue = ClaudeScalar | list[ClaudeValue] | dict[str, ClaudeValue]
type ClaudeRecord = dict[str, ClaudeValue]


class ClaudeParseError(ValueError):
    pass


def parse_claude_jsonl(path: str | Path) -> list[ClaudeRecord]:
    """Parse a Claude JSONL export into object records.

    Args:
        path: Path to the Claude export.

    Returns:
        Parsed Claude records with line numbers attached.

    Raises:
        ClaudeParseError: If the input contains invalid JSON or malformed records.
    """
    records: list[ClaudeRecord] = []
    source_path = Path(path)

    with source_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ClaudeParseError(
                    f"invalid Claude JSONL at {source_path}:{line_number}"
                ) from exc

            if not isinstance(payload, dict):
                raise ClaudeParseError(
                    f"expected object record at {source_path}:{line_number}"
                )

            record_type = payload.get("record_type")
            if not isinstance(record_type, str) or not record_type:
                legacy_record_type = payload.get("type")
                if isinstance(legacy_record_type, str) and legacy_record_type:
                    payload = {**payload, "record_type": legacy_record_type}
                    record_type = legacy_record_type

            if not isinstance(record_type, str) or not record_type:
                raise ClaudeParseError(
                    f"missing record_type/type at {source_path}:{line_number}"
                )

            records.append({**payload, "_line_number": line_number})

    return records
