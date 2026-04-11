from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from snowiki.storage.zones import isoformat_utc

from .cache import TTLQueryCache
from .warm_index import WarmIndexManager


@dataclass(frozen=True, slots=True)
class InvalidationEvent:
    kind: str
    reason: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    triggered_at: str = field(default_factory=lambda: isoformat_utc(None))


class CacheInvalidationManager:
    def __init__(
        self,
        warm_indexes: WarmIndexManager,
        cache: TTLQueryCache,
    ) -> None:
        self.warm_indexes = warm_indexes
        self.cache = cache

    def handle(self, event: InvalidationEvent) -> dict[str, Any]:
        invalidated_entries = self.cache.invalidate()
        snapshot = self.warm_indexes.reload()
        return {
            "ok": True,
            "event": event.kind,
            "reason": event.reason,
            "triggered_at": event.triggered_at,
            "invalidated_entries": invalidated_entries,
            "generation": snapshot.generation,
            "normalized_count": snapshot.normalized_count,
            "compiled_count": snapshot.compiled_count,
        }

    def on_ingest(self, *, reason: str = "ingest") -> dict[str, Any]:
        return self.handle(InvalidationEvent(kind="ingest", reason=reason))

    def on_rebuild(self, *, reason: str = "rebuild") -> dict[str, Any]:
        return self.handle(InvalidationEvent(kind="rebuild", reason=reason))
