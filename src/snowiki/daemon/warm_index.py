from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from snowiki.compiler import CompilerEngine
from snowiki.search import (
    InvertedIndex,
    LexicalIndex,
    WikiIndex,
    build_blended_index,
    build_lexical_index,
    build_wiki_index,
)
from snowiki.search.workspace import (
    compiled_page_to_search_mapping,
    normalized_record_to_search_mapping,
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
        pages = compiler.build_pages(records)

        lexical = build_lexical_index(
            normalized_record_to_search_mapping(record) for record in records
        )
        wiki = build_wiki_index(compiled_page_to_search_mapping(page) for page in pages)
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
