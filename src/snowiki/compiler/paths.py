from __future__ import annotations

import hashlib

from .taxonomy import (
    NormalizedRecord,
    PageType,
    compiled_page_path,
    record_title,
    slugify,
)

MAX_SUMMARY_SLUG_LENGTH = 120


def summary_slug_for_record(record: NormalizedRecord) -> str:
    base = slugify(f"{record.source_type}-{record_title(record)}-{record.id}")
    if len(base) <= MAX_SUMMARY_SLUG_LENGTH:
        return base
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]
    prefix_length = MAX_SUMMARY_SLUG_LENGTH - len(digest) - 1
    prefix = base[:prefix_length].rstrip("-") or "summary"
    return f"{prefix}-{digest}"


def summary_path_for_record(record: NormalizedRecord) -> str:
    return compiled_page_path(PageType.SUMMARY, summary_slug_for_record(record))


def session_slug_for_id(session_id: str) -> str:
    return slugify(session_id)


def session_path_for_id(session_id: str) -> str:
    return compiled_page_path(PageType.SESSION, session_slug_for_id(session_id))
