from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from snowiki.schema.compiled import (
    CompiledPage as _CompiledPage,
)
from snowiki.schema.compiled import (
    PageSection as _PageSection,
)
from snowiki.schema.compiled import (
    PageType as _PageType,
)
from snowiki.schema.compiled import (
    compiled_page_path as _compiled_page_path,
)
from snowiki.schema.normalized import NormalizedRecord as _NormalizedRecord
from snowiki.storage.provenance import dedupe_raw_refs
from snowiki.storage.zones import ensure_utc_datetime

__all__ = [
    "append_section",
    "iso_to_date",
    "merge_raw_refs",
    "merge_string_list",
    "record_session_id",
    "sorted_unique",
    "upsert_page",
]


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
    target[:] = dedupe_raw_refs([*target, *values], sort=True)


def append_section(page: _CompiledPage, title: str, body: str) -> None:
    cleaned = body.strip()
    if not cleaned:
        return
    page.sections.append(_PageSection(title=title, body=cleaned))


def upsert_page(
    pages: dict[str, _CompiledPage],
    *,
    page_type: _PageType,
    slug: str,
    title: str,
    created: str,
    updated: str,
    summary: str = "",
) -> _CompiledPage:
    path = _compiled_page_path(page_type, slug)
    page = pages.get(path)
    if page is None:
        page = _CompiledPage(
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


def record_session_id(record: _NormalizedRecord) -> str | None:
    if record.record_type == "session":
        return record.id
    session_id = record.payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None
