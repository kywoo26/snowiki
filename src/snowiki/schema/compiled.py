from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PageType(StrEnum):
    SUMMARY = "summary"
    CONCEPT = "concept"
    ENTITY = "entity"
    TOPIC = "topic"
    QUESTION = "question"
    PROJECT = "project"
    DECISION = "decision"
    SESSION = "session"
    INDEX = "index"
    LOG = "log"
    OVERVIEW = "overview"


PAGE_DIRECTORIES: dict[PageType, str | None] = {
    PageType.SUMMARY: "summaries",
    PageType.CONCEPT: "concepts",
    PageType.ENTITY: "entities",
    PageType.TOPIC: "topics",
    PageType.QUESTION: "questions",
    PageType.PROJECT: "projects",
    PageType.DECISION: "decisions",
    PageType.SESSION: "sessions",
    PageType.INDEX: None,
    PageType.LOG: None,
    PageType.OVERVIEW: None,
}


@dataclass(slots=True)
class PageSection:
    title: str
    body: str


@dataclass(slots=True)
class TaxonomyItem:
    title: str
    page_type: PageType
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompiledPage:
    page_type: PageType
    slug: str
    title: str
    created: str
    updated: str
    summary: str = ""
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sections: list[PageSection] = field(default_factory=list)
    raw_refs: list[dict[str, Any]] = field(default_factory=list)
    record_ids: list[str] = field(default_factory=list)
    extra_frontmatter: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return compiled_page_path(self.page_type, self.slug)


def page_directory(page_type: PageType) -> str | None:
    return PAGE_DIRECTORIES[page_type]


def compiled_page_path(page_type: PageType, slug: str) -> str:
    if page_type is PageType.INDEX:
        return "compiled/index.md"
    if page_type is PageType.LOG:
        return "compiled/log.md"
    if page_type is PageType.OVERVIEW:
        return "compiled/overview.md"
    directory = page_directory(page_type)
    if directory is None:
        return "compiled/overview.md"
    return f"compiled/{directory}/{slug}.md"


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")
    return lowered or "untitled"


def normalize_taxonomy_items(
    value: Any,
    *,
    page_type: PageType,
) -> list[TaxonomyItem]:
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        items = [value]
    elif isinstance(value, Iterable):
        items = list(value)
    else:
        return []

    normalized: list[TaxonomyItem] = []
    for item in items:
        if isinstance(item, str):
            title = item.strip()
            if not title:
                continue
            normalized.append(TaxonomyItem(title=title, page_type=page_type))
            continue

        if not isinstance(item, Mapping):
            continue

        item_mapping = {str(key): value for key, value in item.items()}

        title = str(
            item_mapping.get("title")
            or item_mapping.get("name")
            or item_mapping.get("id")
            or ""
        ).strip()
        if not title:
            continue

        summary = str(
            item_mapping.get("summary") or item_mapping.get("description") or ""
        ).strip()
        tags = normalize_string_values(item_mapping.get("tags"))
        metadata = {
            key: value
            for key, value in item_mapping.items()
            if key not in {"title", "name", "id", "summary", "description", "tags"}
        }
        normalized.append(
            TaxonomyItem(
                title=title,
                page_type=page_type,
                summary=summary,
                tags=tags,
                metadata=metadata,
            )
        )
    return normalized


def normalize_string_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable):
        values = [item for item in value if isinstance(item, str)]
    else:
        return []
    return sorted({item.strip() for item in values if item.strip()})


__all__ = [
    "CompiledPage",
    "PAGE_DIRECTORIES",
    "PageSection",
    "PageType",
    "TaxonomyItem",
    "compiled_page_path",
    "normalize_string_values",
    "normalize_taxonomy_items",
    "page_directory",
    "slugify",
]
