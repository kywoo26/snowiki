from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from snowiki.compiler import CompilerEngine
from snowiki.search import InvertedIndex, LexicalIndex, WikiIndex
from snowiki.search.workspace import RetrievalService, content_freshness_identity
from snowiki.storage.zones import isoformat_utc


@dataclass(frozen=True, slots=True)
class WarmIndexes:
    lexical: LexicalIndex
    wiki: WikiIndex
    blended: InvertedIndex
    loaded_at: str
    generation: int
    content_identity: dict[str, dict[str, int]]
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

    def health(self) -> dict[str, Any]:
        snapshot = self.get()
        return {
            "owner": "daemon.warm_indexes",
            "loaded_at": snapshot.loaded_at,
            "generation": snapshot.generation,
            "normalized_count": snapshot.normalized_count,
            "compiled_count": snapshot.compiled_count,
            "blended_size": snapshot.blended.size,
            "freshness": self.snapshot_metadata(snapshot),
        }

    def snapshot_metadata(self, snapshot: WarmIndexes | None = None) -> dict[str, Any]:
        current_snapshot = snapshot or self.get()
        current_content_identity = content_freshness_identity(self.root)
        is_stale = current_snapshot.content_identity != current_content_identity
        return {
            "snapshot_owner": "daemon.warm_indexes",
            "loaded_at": current_snapshot.loaded_at,
            "runtime_generation": current_snapshot.generation,
            "content_identity": current_snapshot.content_identity,
            "current_content_identity": current_content_identity,
            "is_stale": is_stale,
            "stale_reason": "content_changed_since_reload" if is_stale else "",
        }

    def _build_snapshot_locked(self) -> WarmIndexes:
        compiler = self._compiler_factory(self.root)
        records = compiler.load_normalized_records()
        pages = compiler.build_pages(records)
        snapshot = RetrievalService.from_records_and_pages(records=records, pages=pages)

        self._generation += 1
        return WarmIndexes(
            lexical=snapshot.lexical,
            wiki=snapshot.wiki,
            blended=snapshot.index,
            loaded_at=isoformat_utc(None),
            generation=self._generation,
            content_identity=content_freshness_identity(self.root),
            normalized_count=snapshot.records_indexed,
            compiled_count=snapshot.pages_indexed,
        )
