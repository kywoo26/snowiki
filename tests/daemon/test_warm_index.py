from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


def _load_snowiki_modules() -> tuple[Any, Any, Any, Any, Any]:
    ttl_query_cache = importlib.import_module("snowiki.daemon.cache").TTLQueryCache
    cache_invalidation_manager = importlib.import_module(
        "snowiki.daemon.invalidation"
    ).CacheInvalidationManager
    warm_index_manager = importlib.import_module(
        "snowiki.daemon.warm_index"
    ).WarmIndexManager
    normalized_storage = importlib.import_module(
        "snowiki.storage.normalized"
    ).NormalizedStorage
    known_item_lookup = importlib.import_module("snowiki.search").known_item_lookup
    return (
        ttl_query_cache,
        cache_invalidation_manager,
        warm_index_manager,
        normalized_storage,
        known_item_lookup,
    )


def test_warm_index_manager_keeps_indexes_loaded_and_searchable(tmp_path: Path) -> None:
    _, _, warm_index_manager_cls, normalized_storage_cls, known_item_lookup = (
        _load_snowiki_modules()
    )

    storage = normalized_storage_cls(tmp_path)
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

    manager = warm_index_manager_cls(tmp_path)
    snapshot = manager.get()
    hits = known_item_lookup(snapshot.blended, "warm index session", limit=3)

    assert snapshot.normalized_count == 1
    assert snapshot.compiled_count >= 1
    assert hits
    assert hits[0].document.title == "Warm Index Session"


def test_invalidation_clears_cache_and_reloads_generation(tmp_path: Path) -> None:
    (
        ttl_query_cache_cls,
        cache_invalidation_manager_cls,
        warm_index_manager_cls,
        normalized_storage_cls,
        known_item_lookup,
    ) = _load_snowiki_modules()

    storage = normalized_storage_cls(tmp_path)
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

    manager = warm_index_manager_cls(tmp_path)
    first_snapshot = manager.get()
    cache = ttl_query_cache_cls(ttl_seconds=30.0)
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

    invalidator = cache_invalidation_manager_cls(manager, cache)
    result = invalidator.on_ingest(reason="new normalized record")
    second_snapshot = manager.get()
    hits = known_item_lookup(second_snapshot.blended, "second session", limit=3)

    assert result["invalidated_entries"] == 1
    assert second_snapshot.generation > first_snapshot.generation
    assert second_snapshot.normalized_count == 2
    assert cache.get("query:first") is None
    assert hits
    assert hits[0].document.title == "Second Session"
