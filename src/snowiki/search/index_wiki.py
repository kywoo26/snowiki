from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .indexer import InvertedIndex, SearchDocument, document_from_mapping


class WikiIndex:
    def __init__(self, documents: Iterable[SearchDocument]) -> None:
        self.documents = tuple(documents)
        self.index = InvertedIndex(self.documents)

    @classmethod
    def from_compiled_pages(cls, pages: Iterable[Mapping[str, Any]]) -> WikiIndex:
        documents = [compiled_page_to_document(page) for page in pages]
        return cls(documents)


def compiled_page_to_document(page: Mapping[str, Any]) -> SearchDocument:
    payload = {
        **page,
        "title": page.get("title") or page.get("path") or page.get("id") or "page",
        "summary": page.get("summary") or page.get("kind") or "compiled wiki page",
    }
    return document_from_mapping(
        payload,
        kind="page",
        source_type="compiled",
        content_keys=("body", "content", "text"),
        recorded_at_keys=("updated_at", "created_at", "recorded_at"),
    )


def build_wiki_index(pages: Iterable[Mapping[str, Any]]) -> WikiIndex:
    return WikiIndex.from_compiled_pages(pages)
