from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .indexer import InvertedIndex, SearchDocument, document_from_mapping


class LexicalIndex:
    def __init__(
        self,
        documents: Iterable[SearchDocument],
        *,
        lexical_policy: str | None = None,
    ) -> None:
        self.documents = tuple(documents)
        self.index = InvertedIndex(self.documents, lexical_policy=lexical_policy)

    @classmethod
    def from_normalized_records(
        cls,
        records: Iterable[Mapping[str, Any]],
        *,
        lexical_policy: str | None = None,
    ) -> LexicalIndex:
        documents = [normalized_record_to_document(record) for record in records]
        return cls(documents, lexical_policy=lexical_policy)


def normalized_record_to_document(record: Mapping[str, Any]) -> SearchDocument:
    title = record.get("title") or record.get("id") or record.get("path") or "record"
    payload = {
        **record,
        "title": title,
        "summary": record.get("summary")
        or record.get("record_type")
        or "normalized record",
    }
    return document_from_mapping(payload, kind="session", source_type="normalized")


def build_lexical_index(
    records: Iterable[Mapping[str, Any]], *, lexical_policy: str | None = None
) -> LexicalIndex:
    return LexicalIndex.from_normalized_records(records, lexical_policy=lexical_policy)
