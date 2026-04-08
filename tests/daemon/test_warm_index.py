from __future__ import annotations

import importlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CompilerEngine = importlib.import_module("snowiki.compiler.engine").CompilerEngine
TTLQueryCache = importlib.import_module("snowiki.daemon.cache").TTLQueryCache
CacheInvalidationManager = importlib.import_module(
    "snowiki.daemon.invalidation"
).CacheInvalidationManager
WarmIndexManager = importlib.import_module("snowiki.daemon.warm_index").WarmIndexManager
NormalizedStorage = importlib.import_module(
    "snowiki.storage.normalized"
).NormalizedStorage
known_item_lookup = importlib.import_module("snowiki.search").known_item_lookup


def test_warm_index_manager_keeps_indexes_loaded_and_searchable(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-1",
        payload={
            "metadata": {"title": "Warm Index Session"},
            "summary": "Keeps a warm search index in memory.",
            "concepts": ["Warm Indexes"],
            "topics": ["Daemon Cache"],
        },
        raw_ref={
            "sha256": "abc123",
            "path": "raw/claude/ab/c123",
            "size": 42,
            "mtime": "2026-04-08T12:00:00Z",
        },
        recorded_at="2026-04-08T12:00:00Z",
    )

    manager = WarmIndexManager(tmp_path)
    snapshot = manager.get()
    hits = known_item_lookup(snapshot.blended, "warm index session", limit=3)

    assert snapshot.normalized_count == 1
    assert snapshot.compiled_count >= 1
    assert hits
    assert hits[0].document.title == "Warm Index Session"


def test_invalidation_clears_cache_and_reloads_generation(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-1",
        payload={
            "metadata": {"title": "First Session"},
            "summary": "Before reload.",
        },
        raw_ref={
            "sha256": "abc123",
            "path": "raw/claude/ab/c123",
            "size": 42,
            "mtime": "2026-04-08T12:00:00Z",
        },
        recorded_at="2026-04-08T12:00:00Z",
    )

    manager = WarmIndexManager(tmp_path)
    first_snapshot = manager.get()
    cache = TTLQueryCache(ttl_seconds=30.0)
    cache.set("query:first", {"ok": True})

    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-2",
        payload={
            "metadata": {"title": "Second Session"},
            "summary": "After reload.",
        },
        raw_ref={
            "sha256": "def456",
            "path": "raw/claude/de/f456",
            "size": 42,
            "mtime": "2026-04-08T12:05:00Z",
        },
        recorded_at="2026-04-08T12:05:00Z",
    )

    invalidator = CacheInvalidationManager(manager, cache)
    result = invalidator.on_ingest(reason="new normalized record")
    second_snapshot = manager.get()
    hits = known_item_lookup(second_snapshot.blended, "second session", limit=3)

    assert result["invalidated_entries"] == 1
    assert second_snapshot.generation > first_snapshot.generation
    assert second_snapshot.normalized_count == 2
    assert cache.get("query:first") is None
    assert hits
    assert hits[0].document.title == "Second Session"
