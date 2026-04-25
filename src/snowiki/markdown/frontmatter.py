from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

type FrontmatterScalar = None | bool | int | float | str
type FrontmatterValue = FrontmatterScalar | list[FrontmatterScalar]

SAFE_FRONTMATTER_FIELDS = frozenset(
    {
        "aliases",
        "date",
        "decisions",
        "description",
        "projects",
        "questions",
        "related",
        "source",
        "status",
        "summary",
        "tags",
        "title",
        "topics",
    }
)

RESERVED_FRONTMATTER_FIELDS = frozenset(
    {
        "id",
        "raw_ref",
        "raw_refs",
        "record_type",
        "recorded_at",
        "record_ids",
        "source_type",
        "sources",
        "snowiki",
        "storage",
        "updated",
        "provenance",
    }
)


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    frontmatter: dict[str, FrontmatterValue]
    promoted: dict[str, FrontmatterValue]
    reserved: dict[str, FrontmatterValue]
    body: str
    text: str


def parse_markdown_document(content: str) -> MarkdownDocument:
    """Parse Markdown body and simple YAML-like frontmatter."""
    frontmatter_text, body = _split_frontmatter(content)
    frontmatter = parse_frontmatter(frontmatter_text) if frontmatter_text else {}
    promoted = {
        key: value
        for key, value in frontmatter.items()
        if key in SAFE_FRONTMATTER_FIELDS and key not in RESERVED_FRONTMATTER_FIELDS
    }
    reserved = {
        key: value for key, value in frontmatter.items() if key in RESERVED_FRONTMATTER_FIELDS
    }
    return MarkdownDocument(
        frontmatter=frontmatter,
        promoted=promoted,
        reserved=reserved,
        body=body,
        text=body.strip(),
    )


def parse_frontmatter(content: str) -> dict[str, FrontmatterValue]:
    """Parse the frontmatter subset Snowiki preserves for deterministic ingest."""
    result: dict[str, FrontmatterValue] = {}
    current_key: str | None = None
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped = raw_line.strip()
        if current_key is not None and stripped.startswith("- "):
            existing = result.setdefault(current_key, [])
            if isinstance(existing, list):
                existing.append(_parse_scalar(stripped[2:].strip()))
            continue

        current_key = None
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue
        stripped_value = value.strip()
        if not stripped_value:
            result[normalized_key] = []
            current_key = normalized_key
            continue
        result[normalized_key] = _parse_value(stripped_value)
    return result


def _split_frontmatter(content: str) -> tuple[str, str]:
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized
    closing = normalized.find("\n---\n", 4)
    if closing == -1:
        return "", normalized
    frontmatter = normalized[4:closing]
    body = normalized[closing + len("\n---\n") :]
    return frontmatter, body


def _parse_value(value: str) -> FrontmatterValue:
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        return _parse_inline_list(value)
    if _is_quoted(value):
        return _unquote(value)
    return _parse_scalar(value)


def _parse_scalar(value: str) -> FrontmatterScalar:
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _parse_inline_list(value: str) -> list[FrontmatterScalar]:
    try:
        parsed = cast(object, json.loads(value))
    except json.JSONDecodeError:
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if not isinstance(parsed, list):
        return [_coerce_json_scalar(parsed)]
    parsed_items = cast(list[object], parsed)
    return [_coerce_json_scalar(item) for item in parsed_items]


def _coerce_json_scalar(value: object) -> FrontmatterScalar:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _is_quoted(value: str) -> bool:
    return (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    )


def _unquote(value: str) -> str:
    if value.startswith('"'):
        try:
            parsed = cast(object, json.loads(value))
        except json.JSONDecodeError:
            return value[1:-1]
        return str(parsed)
    return value[1:-1]
