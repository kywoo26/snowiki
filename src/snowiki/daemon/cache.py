from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float


class TTLQueryCache:
    def __init__(
        self,
        ttl_seconds: float = 30.0,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.ttl_seconds = max(float(ttl_seconds), 0.0)
        self._clock = clock or time.monotonic
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            self._prune_locked()
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> Any:
        expires_at = self._clock() + self.ttl_seconds
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=expires_at)
        return value

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        return self.set(key, factory())

    def invalidate(self, *, prefix: str | None = None) -> int:
        with self._lock:
            if prefix is None:
                count = len(self._entries)
                self._entries.clear()
                return count

            keys = [key for key in self._entries if key.startswith(prefix)]
            for key in keys:
                self._entries.pop(key, None)
            return len(keys)

    def stats(self) -> dict[str, float | int]:
        with self._lock:
            self._prune_locked()
            return {
                "size": len(self._entries),
                "ttl_seconds": self.ttl_seconds,
            }

    def _prune_locked(self) -> None:
        now = self._clock()
        expired_keys = [
            key for key, entry in self._entries.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)
