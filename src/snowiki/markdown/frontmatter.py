from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import cast

import frontmatter as frontmatter_lib
import yaml

from .parser import MarkdownBodyStructure, parse_markdown_body

type FrontmatterScalar = None | bool | int | float | str
type FrontmatterValue = (
    FrontmatterScalar
    | list["FrontmatterValue"]
    | dict[str, "FrontmatterValue"]
)

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
    structure: MarkdownBodyStructure


def parse_markdown_document(content: str) -> MarkdownDocument:
    """Parse Markdown body and frontmatter metadata."""
    try:
        metadata, body = cast(tuple[object, str], frontmatter_lib.parse(content))
    except yaml.YAMLError as exc:
        raise ValueError("invalid YAML frontmatter") from exc
    frontmatter = _coerce_frontmatter_mapping(metadata)
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
        structure=parse_markdown_body(body.strip()),
    )


def parse_frontmatter(content: str) -> dict[str, FrontmatterValue]:
    """Parse an isolated YAML frontmatter payload deterministically."""
    try:
        parsed = cast(object, yaml.safe_load(content))
    except yaml.YAMLError as exc:
        raise ValueError("invalid YAML frontmatter") from exc
    return _coerce_frontmatter_mapping(parsed)


def _coerce_frontmatter_mapping(parsed: object) -> dict[str, FrontmatterValue]:
    if parsed is None:
        return {}
    if not isinstance(parsed, Mapping):
        return {}
    return {
        str(key).strip(): _coerce_frontmatter_value(value)
        for key, value in cast(Mapping[object, object], parsed).items()
        if str(key).strip()
    }


def _coerce_frontmatter_value(value: object) -> FrontmatterValue:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {
            str(key): _coerce_frontmatter_value(item)
            for key, item in sorted(
                cast(Mapping[object, object], value).items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, (list, tuple)):
        sequence = cast(list[object] | tuple[object, ...], value)
        return [_coerce_frontmatter_value(item) for item in sequence]
    if isinstance(value, set):
        items = cast(set[object], value)
        coerced_items: list[FrontmatterValue] = [
            _coerce_frontmatter_value(item) for item in items
        ]
        return cast(FrontmatterValue, sorted(coerced_items, key=str))
    return str(value)
