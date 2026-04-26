from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, cast

from snowiki.storage.zones import ensure_utc_datetime

from .indexer import SearchDocument, SearchValue

if TYPE_CHECKING:
    from .bm25_index import BM25SearchDocument


@dataclass(frozen=True)
class RuntimeCorpusDocument:
    """Typed retrieval corpus document used by the BM25 runtime."""

    id: str
    path: str
    kind: str
    title: str
    content: str
    summary: str = ""
    aliases: tuple[str, ...] = ()
    recorded_at: datetime | None = None
    source_type: str = ""
    metadata: dict[str, SearchValue] = field(default_factory=dict)

    def to_search_document(self) -> SearchDocument:
        return SearchDocument(
            id=self.id,
            path=self.path,
            kind=self.kind,
            title=self.title,
            content=self.content,
            summary=self.summary,
            aliases=self.aliases,
            recorded_at=self.recorded_at,
            source_type=self.source_type,
            metadata=dict(self.metadata),
        )

    def to_bm25_document(self) -> BM25SearchDocument:
        from .bm25_index import BM25SearchDocument

        return BM25SearchDocument(
            id=self.id,
            path=self.path,
            kind=self.kind,
            title=self.title,
            content=self.content,
            summary=self.summary,
            aliases=self.aliases,
            recorded_at=self.recorded_at,
            source_type=self.source_type,
        )


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


def _recorded_at(payload: Mapping[str, object], keys: Iterable[str]) -> datetime | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, datetime | str):
            return ensure_utc_datetime(value)
    return None


def runtime_document_from_normalized_mapping(
    record: Mapping[str, object],
) -> RuntimeCorpusDocument:
    title = _stringify(record.get("title") or record.get("id") or record.get("path"))
    title = title or "record"
    summary = _stringify(
        record.get("summary") or record.get("record_type") or "normalized record"
    )
    content_parts = [
        title,
        _stringify(record.get("path") or record.get("id") or title),
        summary,
        _stringify(record.get("content")),
        _stringify(record.get("text")),
        _stringify(record.get("body")),
        _stringify(record),
    ]
    path = _stringify(record.get("path") or record.get("id") or title)
    metadata_payload: dict[str, object] = {
        **dict(record),
        "title": title,
        "summary": summary,
    }
    return RuntimeCorpusDocument(
        id=_stringify(record.get("id") or path),
        path=path,
        kind="session",
        title=title,
        content="\n".join(part for part in content_parts if part),
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
    page: Mapping[str, object],
) -> RuntimeCorpusDocument:
    title = _stringify(page.get("title") or page.get("path") or page.get("id"))
    title = title or "page"
    summary = _stringify(page.get("summary") or page.get("kind") or "compiled wiki page")
    content_parts = [
        title,
        _stringify(page.get("path") or page.get("id") or title),
        summary,
        _stringify(page.get("body")),
        _stringify(page.get("content")),
        _stringify(page.get("text")),
        _stringify(page),
    ]
    path = _stringify(page.get("path") or page.get("id") or title)
    metadata_payload: dict[str, object] = {
        **dict(page),
        "title": title,
        "summary": summary,
    }
    return RuntimeCorpusDocument(
        id=_stringify(page.get("id") or path),
        path=path,
        kind="page",
        title=title,
        content="\n".join(part for part in content_parts if part),
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
) -> tuple[RuntimeCorpusDocument, ...]:
    return tuple(
        [runtime_document_from_normalized_mapping(record) for record in records]
        + [runtime_document_from_compiled_page(page) for page in pages]
    )
