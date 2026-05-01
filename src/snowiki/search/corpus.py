from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import cast

from snowiki.compiler.taxonomy import CompiledPage, NormalizedRecord, PageSection
from snowiki.storage.zones import ensure_utc_datetime

from .models import SearchDocument, SearchValue


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return " ".join(_stringify(item) for item in mapping.values())
    if isinstance(value, list | tuple | set):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _search_value(value: object) -> SearchValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _search_value(item) for key, item in mapping.items()}
    if isinstance(value, list | tuple | set):
        return [_search_value(item) for item in value]
    return str(value)


def _metadata(payload: Mapping[str, object]) -> dict[str, SearchValue]:
    return {str(key): _search_value(value) for key, value in payload.items()}


def _aliases(payload: Mapping[str, object], keys: Iterable[str]) -> tuple[str, ...]:
    aliases: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            aliases.append(value)
        elif isinstance(value, list | tuple | set):
            items = cast(Iterable[object], value)
            aliases.extend(_stringify(item) for item in items if _stringify(item))
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _text_content(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, list | tuple | set):
        items = cast(Iterable[object], value)
        return "\n".join(text for item in items if (text := _text_content(item)))
    return ""


def _body_text(payload: Mapping[str, object], keys: Iterable[str]) -> str:
    return "\n".join(text for key in keys if (text := _text_content(payload.get(key))))


def page_body(sections: list[PageSection]) -> str:
    return "\n\n".join(f"{section.title}\n{section.body}" for section in sections)


def search_document_from_normalized_record(record: NormalizedRecord) -> SearchDocument:
    metadata = record.payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, Mapping) else {}
    title = _stringify(
        metadata_map.get("title")
        or metadata_map.get("name")
        or record.payload.get("title")
        or record.id
    )
    summary = _stringify(record.payload.get("summary") or record.record_type)
    content = _body_text(record.payload, ("content", "text", "body"))
    raw_ref = record.raw_refs[0] if record.raw_refs else None
    metadata_payload: dict[str, object] = {
        **record.payload,
        "id": record.id,
        "path": record.path,
        "title": title,
        "content": content,
        "text": content,
        "metadata": dict(cast(Mapping[str, object], metadata_map)),
        "raw_ref": raw_ref,
        "record_type": record.record_type,
        "recorded_at": record.recorded_at,
        "summary": summary,
    }
    return SearchDocument(
        id=record.id,
        path=record.path,
        kind="session",
        title=title,
        content=content,
        summary=summary,
        aliases=_aliases(record.payload, ("aliases", "tags")),
        recorded_at=ensure_utc_datetime(record.recorded_at) if record.recorded_at else None,
        source_type="normalized",
        metadata=_metadata(metadata_payload),
    )


def search_document_from_compiled_page(page: CompiledPage) -> SearchDocument:
    content = page_body(page.sections)
    summary = page.summary or page.page_type.value
    metadata_payload: dict[str, object] = {
        **page.extra_frontmatter,
        "id": page.path,
        "path": page.path,
        "title": page.title,
        "summary": summary,
        "body": content,
        "tags": page.tags,
        "related": page.related,
        "record_ids": page.record_ids,
        "updated_at": page.updated,
    }
    return SearchDocument(
        id=page.path,
        path=page.path,
        kind="page",
        title=page.title,
        content=content,
        summary=summary,
        aliases=tuple(page.tags),
        recorded_at=ensure_utc_datetime(page.updated) if page.updated else None,
        source_type="compiled",
        metadata=_metadata(metadata_payload),
    )


def _recorded_at(payload: Mapping[str, object], keys: Iterable[str]) -> datetime | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, datetime | str):
            return ensure_utc_datetime(value)
    return None


def runtime_document_from_normalized_mapping(
    record: Mapping[str, object] | NormalizedRecord,
) -> SearchDocument:
    """Compatibility wrapper for mapping-based normalized records."""

    if isinstance(record, NormalizedRecord):
        return search_document_from_normalized_record(record)
    title = _stringify(record.get("title") or record.get("id") or record.get("path"))
    title = title or "record"
    summary = _stringify(
        record.get("summary") or record.get("record_type") or "normalized record"
    )
    content = _body_text(record, ("content", "text", "body"))
    path = _stringify(record.get("path") or record.get("id") or title)
    metadata_payload: dict[str, object] = {
        **dict(record),
        "title": title,
        "summary": summary,
    }
    return SearchDocument(
        id=_stringify(record.get("id") or path),
        path=path,
        kind="session",
        title=title,
        content=content,
        summary=summary,
        aliases=_aliases(record, ("aliases", "tags", "identity_keys")),
        recorded_at=_recorded_at(
            record,
            ("recorded_at", "updated_at", "created_at", "timestamp", "started_at"),
        ),
        source_type="normalized",
        metadata=_metadata(metadata_payload),
    )


def runtime_document_from_compiled_page(
    page: Mapping[str, object] | CompiledPage,
) -> SearchDocument:
    """Compatibility wrapper for mapping-based compiled pages."""

    if isinstance(page, CompiledPage):
        return search_document_from_compiled_page(page)
    title = _stringify(page.get("title") or page.get("path") or page.get("id"))
    title = title or "page"
    summary = _stringify(page.get("summary") or page.get("kind") or "compiled wiki page")
    content = _body_text(page, ("body", "content", "text"))
    path = _stringify(page.get("path") or page.get("id") or title)
    metadata_payload: dict[str, object] = {
        **dict(page),
        "title": title,
        "summary": summary,
    }
    return SearchDocument(
        id=_stringify(page.get("id") or path),
        path=path,
        kind="page",
        title=title,
        content=content,
        summary=summary,
        aliases=_aliases(page, ("aliases", "tags", "identity_keys")),
        recorded_at=_recorded_at(page, ("updated_at", "created_at", "recorded_at")),
        source_type="compiled",
        metadata=_metadata(metadata_payload),
    )


def runtime_corpus_from_mappings(
    *,
    records: Iterable[Mapping[str, object]],
    pages: Iterable[Mapping[str, object]],
) -> tuple[SearchDocument, ...]:
    return tuple(
        [runtime_document_from_normalized_mapping(record) for record in records]
        + [runtime_document_from_compiled_page(page) for page in pages]
    )


def runtime_corpus_from_records_and_pages(
    *,
    records: Iterable[NormalizedRecord],
    pages: Iterable[CompiledPage],
) -> tuple[SearchDocument, ...]:
    return tuple(
        [search_document_from_normalized_record(record) for record in records]
        + [search_document_from_compiled_page(page) for page in pages]
    )
