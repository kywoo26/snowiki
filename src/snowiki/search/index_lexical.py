from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .corpus import runtime_document_from_normalized_mapping
from .indexer import InvertedIndex, SearchDocument
from .registry import SearchTokenizer


class LexicalIndex:
    def __init__(
        self,
        documents: Iterable[SearchDocument],
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> None:
        self.documents = tuple(documents)
        self.index = InvertedIndex(self.documents, tokenizer=tokenizer)

    @classmethod
    def from_normalized_records(
        cls,
        records: Iterable[Mapping[str, Any]],
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> LexicalIndex:
        documents = [normalized_record_to_document(record) for record in records]
        return cls(documents, tokenizer=tokenizer)


def normalized_record_to_document(record: Mapping[str, Any]) -> SearchDocument:
    return runtime_document_from_normalized_mapping(record).to_search_document()


def build_lexical_index(
    records: Iterable[Mapping[str, Any]],
    *,
    tokenizer: SearchTokenizer | None = None,
) -> LexicalIndex:
    return LexicalIndex.from_normalized_records(records, tokenizer=tokenizer)
