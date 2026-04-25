from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from snowiki.storage.zones import ensure_utc_datetime


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
class NormalizedRecord:
    id: str
    path: str
    source_type: str
    record_type: str
    recorded_at: str
    payload: dict[str, Any]
    raw_refs: list[dict[str, Any]]


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


def iso_to_date(value: str | None) -> str:
    if not value:
        return ensure_utc_datetime(None).date().isoformat()
    return ensure_utc_datetime(value).date().isoformat()


def sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def merge_string_list(target: list[str], values: Iterable[str]) -> None:
    target[:] = sorted_unique([*target, *values])


def merge_raw_refs(
    target: list[dict[str, Any]], values: Iterable[Mapping[str, Any]]
) -> None:
    seen = {
        (str(entry.get("sha256", "")), str(entry.get("path", ""))) for entry in target
    }
    for value in values:
        raw_ref = dict(value)
        key = (str(raw_ref.get("sha256", "")), str(raw_ref.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        target.append(raw_ref)
    target.sort(
        key=lambda entry: (str(entry.get("path", "")), str(entry.get("sha256", "")))
    )


def append_section(page: CompiledPage, title: str, body: str) -> None:
    cleaned = body.strip()
    if not cleaned:
        return
    page.sections.append(PageSection(title=title, body=cleaned))


def upsert_page(
    pages: dict[str, CompiledPage],
    *,
    page_type: PageType,
    slug: str,
    title: str,
    created: str,
    updated: str,
    summary: str = "",
) -> CompiledPage:
    path = compiled_page_path(page_type, slug)
    page = pages.get(path)
    if page is None:
        page = CompiledPage(
            page_type=page_type,
            slug=slug,
            title=title,
            created=created,
            updated=updated,
            summary=summary.strip(),
        )
        pages[path] = page
        return page

    page.created = min(page.created, created)
    page.updated = max(page.updated, updated)
    if not page.summary and summary.strip():
        page.summary = summary.strip()
    return page


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
    return sorted_unique(item.strip() for item in values if item.strip())


def record_session_id(record: NormalizedRecord) -> str | None:
    if record.record_type == "session":
        return record.id
    session_id = record.payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None
