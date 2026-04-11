from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from snowiki.compiler import CompiledPage, CompilerEngine, NormalizedRecord
from snowiki.search import (
    InvertedIndex,
    LexicalIndex,
    WikiIndex,
    build_blended_index,
    build_lexical_index,
    build_wiki_index,
)
from snowiki.storage.zones import isoformat_utc


@dataclass(frozen=True, slots=True)
class WarmIndexes:
    lexical: LexicalIndex
    wiki: WikiIndex
    blended: InvertedIndex
    loaded_at: str
    generation: int
    normalized_count: int
    compiled_count: int


class WarmIndexManager:
    def __init__(
        self,
        root: str | Path,
        *,
        compiler_factory: type[CompilerEngine] = CompilerEngine,
    ) -> None:
        self.root = Path(root)
        self._compiler_factory = compiler_factory
        self._lock = Lock()
        self._snapshot: WarmIndexes | None = None
        self._generation = 0

    def get(self) -> WarmIndexes:
        with self._lock:
            if self._snapshot is None:
                self._snapshot = self._build_snapshot_locked()
            return self._snapshot

    def reload(self) -> WarmIndexes:
        with self._lock:
            self._snapshot = self._build_snapshot_locked()
            return self._snapshot

    def health(self) -> dict[str, int | str]:
        snapshot = self.get()
        return {
            "loaded_at": snapshot.loaded_at,
            "generation": snapshot.generation,
            "normalized_count": snapshot.normalized_count,
            "compiled_count": snapshot.compiled_count,
            "blended_size": snapshot.blended.size,
        }

    def _build_snapshot_locked(self) -> WarmIndexes:
        compiler = self._compiler_factory(self.root)
        records = compiler.load_normalized_records()
        pages = compiler.build_pages()

        lexical = build_lexical_index(
            self._normalized_record_payload(record) for record in records
        )
        wiki = build_wiki_index(self._compiled_page_payload(page) for page in pages)
        blended = build_blended_index(lexical.documents, wiki.documents)

        self._generation += 1
        return WarmIndexes(
            lexical=lexical,
            wiki=wiki,
            blended=blended,
            loaded_at=isoformat_utc(None),
            generation=self._generation,
            normalized_count=len(records),
            compiled_count=len(pages),
        )

    def _normalized_record_payload(self, record: NormalizedRecord) -> dict[str, Any]:
        metadata = record.payload.get("metadata")
        title = ""
        if isinstance(metadata, dict):
            title = str(metadata.get("title") or metadata.get("name") or "").strip()
        title = title or str(record.payload.get("title") or record.id)
        return {
            **record.payload,
            "id": record.id,
            "path": record.path,
            "title": title,
            "record_type": record.record_type,
            "recorded_at": record.recorded_at,
        }

    def _compiled_page_payload(self, page: CompiledPage) -> dict[str, Any]:
        rendered_sections = "\n\n".join(
            f"## {section.title}\n{section.body}" for section in page.sections
        )
        return {
            "id": page.path,
            "path": page.path,
            "title": page.title,
            "kind": page.page_type.value,
            "summary": page.summary,
            "body": rendered_sections,
            "content": rendered_sections,
            "tags": page.tags,
            "updated_at": page.updated,
            "created_at": page.created,
            "sources": page.sources,
            "record_ids": page.record_ids,
        }
