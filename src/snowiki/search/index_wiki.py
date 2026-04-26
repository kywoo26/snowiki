from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .corpus import runtime_document_from_compiled_page
from .indexer import InvertedIndex, SearchDocument
from .registry import SearchTokenizer


class WikiIndex:
    def __init__(
        self,
        documents: Iterable[SearchDocument],
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> None:
        self.documents = tuple(documents)
        self.index = InvertedIndex(self.documents, tokenizer=tokenizer)

    @classmethod
    def from_compiled_pages(
        cls,
        pages: Iterable[Mapping[str, Any]],
        *,
        tokenizer: SearchTokenizer | None = None,
    ) -> WikiIndex:
        documents = [compiled_page_to_document(page) for page in pages]
        return cls(documents, tokenizer=tokenizer)


def compiled_page_to_document(page: Mapping[str, Any]) -> SearchDocument:
    return runtime_document_from_compiled_page(page).to_search_document()


def build_wiki_index(
    pages: Iterable[Mapping[str, Any]],
    *,
    tokenizer: SearchTokenizer | None = None,
) -> WikiIndex:
    return WikiIndex.from_compiled_pages(pages, tokenizer=tokenizer)
