from __future__ import annotations

from .taxonomy import (
    NormalizedRecord,
    PageType,
    compiled_page_path,
    record_title,
    slugify,
)


def summary_slug_for_record(record: NormalizedRecord) -> str:
    return slugify(f"{record.source_type}-{record_title(record)}-{record.id}")


def summary_path_for_record(record: NormalizedRecord) -> str:
    return compiled_page_path(PageType.SUMMARY, summary_slug_for_record(record))


def session_slug_for_id(session_id: str) -> str:
    return slugify(session_id)


def session_path_for_id(session_id: str) -> str:
    return compiled_page_path(PageType.SESSION, session_slug_for_id(session_id))
