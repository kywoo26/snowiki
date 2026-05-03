from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import NotRequired, TypedDict, cast

from snowiki.schema.compiled import (
    PageType,
    TaxonomyItem,
    normalize_taxonomy_items,
    slugify,
)
from snowiki.schema.normalized import NormalizedRecord


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


def empty_projection_taxonomy() -> dict[str, list[object]]:
    """Return the strict empty taxonomy shape required by compiler projections."""
    return {bucket: [] for bucket, _page_type in TAXONOMY_BUCKETS}


def make_compiler_projection(
    *,
    title: str,
    summary: str,
    body: str | None = None,
    tags: Sequence[str] = (),
    source_identity: SourceIdentity | None = None,
    sections: Sequence[ProjectionSection] = (),
    taxonomy: Mapping[str, Sequence[object]] | None = None,
) -> CompilerProjection:
    """Build the normalized compiler projection contract for active writers."""
    identity: SourceIdentity = {} if source_identity is None else source_identity
    projection: CompilerProjection = {
        "title": title,
        "summary": summary,
        "tags": list(tags),
        "source_identity": identity,
        "sections": list(sections),
        "taxonomy": _projection_taxonomy(taxonomy),
    }
    if body is not None:
        projection["body"] = body
    return projection


def projection_for_record(record: NormalizedRecord) -> Mapping[str, object]:
    """Return the required compiler projection mapping for a record."""
    projection = record.payload.get("projection")
    if isinstance(projection, Mapping):
        return cast(Mapping[str, object], projection)
    raise ValueError(f"normalized record `{record.path}` is missing compiler projection")


def projected_title(record: NormalizedRecord) -> str:
    """Return the projected compiler title for a record."""
    title = projection_for_record(record).get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    raise ValueError(f"normalized record `{record.path}` projection.title is required")


def projected_summary(record: NormalizedRecord) -> str:
    """Return the projected compiler summary for a record."""
    projection = projection_for_record(record)
    summary = projection.get("summary")
    if isinstance(summary, str):
        return summary.strip()
    raise ValueError(f"normalized record `{record.path}` projection.summary is required")


def projected_tags(record: NormalizedRecord) -> list[str]:
    """Return tags projected for compiler use."""
    projection = projection_for_record(record)
    tags = projection.get("tags")
    if isinstance(tags, Iterable) and not isinstance(tags, (str, bytes, Mapping)):
        return sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()})
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

    return []


def projected_taxonomy_items(record: NormalizedRecord) -> list[TaxonomyItem]:
    """Return taxonomy items from the required compiler projection."""
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

    return []


def _projection_taxonomy(
    taxonomy: Mapping[str, Sequence[object]] | None,
) -> dict[str, list[object]]:
    if taxonomy is None:
        return empty_projection_taxonomy()
    return {
        bucket: list(taxonomy.get(bucket, ()))
        for bucket, _page_type in TAXONOMY_BUCKETS
    }


__all__ = [
    "CompilerProjection",
    "ProjectionSection",
    "SourceIdentity",
    "TAXONOMY_BUCKETS",
    "empty_projection_taxonomy",
    "make_compiler_projection",
    "projected_sections",
    "projected_source_identity",
    "projected_summary",
    "projected_tags",
    "projected_taxonomy_items",
    "projected_title",
    "projection_for_record",
]
