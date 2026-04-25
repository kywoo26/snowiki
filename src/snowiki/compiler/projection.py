from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, NotRequired, TypedDict, cast

from .taxonomy import (
    NormalizedRecord,
    PageType,
    TaxonomyItem,
    normalize_taxonomy_items,
    slugify,
)


class ProjectionSection(TypedDict):
    """Compiler-facing section projected from a normalized record."""

    title: str
    body: str


class SourceIdentity(TypedDict, total=False):
    """Stable source identity fields exposed to compiled pages."""

    source_root: str
    relative_path: str
    content_hash: str


class CompilerProjection(TypedDict):
    """Source-agnostic compiler projection stored in normalized payloads."""

    title: str
    summary: str
    body: NotRequired[str]
    tags: list[str]
    source_identity: SourceIdentity
    sections: list[ProjectionSection]
    taxonomy: dict[str, list[object]]


TAXONOMY_BUCKETS: tuple[tuple[str, PageType], ...] = (
    ("concepts", PageType.CONCEPT),
    ("entities", PageType.ENTITY),
    ("topics", PageType.TOPIC),
    ("questions", PageType.QUESTION),
    ("projects", PageType.PROJECT),
    ("decisions", PageType.DECISION),
)


def projection_for_record(record: NormalizedRecord) -> Mapping[str, object]:
    """Return the compiler projection mapping for a record, if present."""
    projection = record.payload.get("projection")
    if isinstance(projection, Mapping):
        return cast(Mapping[str, object], projection)
    return {}


def projected_title(record: NormalizedRecord, fallback: str) -> str:
    """Return the projection title or a legacy fallback title."""
    title = projection_for_record(record).get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return fallback


def projected_summary(record: NormalizedRecord, fallback: str) -> str:
    """Return the projection summary or a legacy fallback summary."""
    projection = projection_for_record(record)
    summary = projection.get("summary")
    if isinstance(summary, str):
        return summary.strip()

    legacy_summary = record.payload.get("summary")
    if isinstance(legacy_summary, str):
        return legacy_summary.strip()
    return fallback


def projected_tags(record: NormalizedRecord) -> list[str]:
    """Return tags projected for compiler use, including legacy frontmatter tags."""
    projection = projection_for_record(record)
    tags = projection.get("tags")
    if isinstance(tags, Iterable) and not isinstance(tags, (str, bytes, Mapping)):
        return sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()})

    promoted = record.payload.get("promoted_frontmatter")
    if isinstance(promoted, Mapping):
        promoted_tags = promoted.get("tags")
        if isinstance(promoted_tags, Iterable) and not isinstance(
            promoted_tags, (str, bytes, Mapping)
        ):
            return sorted(
                {
                    tag.strip()
                    for tag in promoted_tags
                    if isinstance(tag, str) and tag.strip()
                }
            )
    return []


def projected_source_identity(record: NormalizedRecord) -> SourceIdentity:
    """Return source identity fields projected for compiler output."""
    projection = projection_for_record(record)
    source_identity = projection.get("source_identity")
    fields: SourceIdentity = {}
    if isinstance(source_identity, Mapping):
        source_identity_map = cast(Mapping[str, object], source_identity)
        for key in ("source_root", "relative_path", "content_hash"):
            value = source_identity_map.get(key)
            if isinstance(value, str) and value:
                fields[key] = value
        if fields:
            return fields

    for key in ("source_root", "relative_path", "content_hash"):
        value = record.payload.get(key)
        if isinstance(value, str) and value:
            fields[key] = value
    return fields


def projected_sections(record: NormalizedRecord) -> list[ProjectionSection]:
    """Return compiler-facing sections for a record."""
    projection = projection_for_record(record)
    sections = projection.get("sections")
    if isinstance(sections, Iterable) and not isinstance(sections, (str, bytes, Mapping)):
        projected: list[ProjectionSection] = []
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            section_map = cast(Mapping[str, object], section)
            title = section_map.get("title")
            body = section_map.get("body")
            if isinstance(title, str) and isinstance(body, str):
                projected.append({"title": title, "body": body})
        if projected:
            return projected

    if record.record_type == "document":
        text = record.payload.get("text")
        if isinstance(text, str) and text.strip():
            return [{"title": "Document", "body": text}]
    return []


def projected_taxonomy_items(record: NormalizedRecord) -> list[TaxonomyItem]:
    """Return taxonomy items from projection first, then legacy payload buckets."""
    taxonomy = projection_for_record(record).get("taxonomy")
    items: list[TaxonomyItem] = []
    if isinstance(taxonomy, Mapping):
        taxonomy_map = cast(Mapping[str, object], taxonomy)
        for key, page_type in TAXONOMY_BUCKETS:
            items.extend(
                normalize_taxonomy_items(
                    taxonomy_map.get(key),
                    page_type=page_type,
                )
            )
        items.sort(
            key=lambda item: (item.page_type.value, slugify(item.title), item.title.lower())
        )
        return items

    for key, page_type in TAXONOMY_BUCKETS:
        items.extend(
            normalize_taxonomy_items(
                _legacy_compiler_bucket(record, key),
                page_type=page_type,
            )
        )
    items.sort(key=lambda item: (item.page_type.value, slugify(item.title), item.title.lower()))
    return items


def _legacy_compiler_bucket(record: NormalizedRecord, key: str) -> Any:
    compiler = record.payload.get("compiler")
    if isinstance(compiler, Mapping) and key in compiler:
        return compiler[key]
    return record.payload.get(key)
