from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


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

    assert snapshot.lexical_policy == "legacy-lexical"
    assert snapshot.lexical_policy_version == 1
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
    assert result["event"] == "ingest"
    assert result["reason"] == "new normalized record"
    assert result["triggered_at"].endswith("Z")
    assert result["owners"] == {
        "cache": "daemon.response_cache",
        "snapshot": "daemon.warm_indexes",
    }
    assert result["freshness"]["snapshot_owner"] == "daemon.warm_indexes"
    assert result["freshness"]["runtime_generation"] == second_snapshot.generation
    assert result["freshness"]["lexical_policy"] == second_snapshot.lexical_policy
    assert result["freshness"]["lexical_policy_version"] == 1
    assert result["freshness"]["content_identity"] == second_snapshot.content_identity
    assert result["freshness"]["is_stale"] is False
    assert second_snapshot.generation > first_snapshot.generation
    assert second_snapshot.normalized_count == 2
    assert cache.get("query:first") is None
    assert hits
    assert hits[0].document.title == "Second Session"


def test_warm_index_health_surfaces_content_identity_and_stale_state(
    tmp_path: Path,
) -> None:
    _, _, warm_index_manager_cls, normalized_storage_cls, _ = _load_snowiki_modules()

    storage = normalized_storage_cls(tmp_path)
    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-1",
        payload={
            "metadata": {"title": "First Session"},
            "summary": "Before stale state.",
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

    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-2",
        payload={
            "metadata": {"title": "Second Session"},
            "summary": "Introduces stale state.",
        },
        raw_ref={
            "sha256": "def456",
            "path": "raw/claude/de/f456",
            "size": 42,
            "mtime": "2026-04-08T12:05:00Z",
        },
        recorded_at="2026-04-08T12:05:00Z",
    )

    health = manager.health()

    assert health["owner"] == "daemon.warm_indexes"
    assert health["generation"] == snapshot.generation
    assert health["lexical_policy"] == snapshot.lexical_policy
    assert health["lexical_policy_version"] == 1
    assert health["freshness"]["snapshot_owner"] == "daemon.warm_indexes"
    assert health["freshness"]["runtime_generation"] == snapshot.generation
    assert health["freshness"]["lexical_policy"] == snapshot.lexical_policy
    assert health["freshness"]["lexical_policy_version"] == 1
    assert health["freshness"]["content_identity"] == snapshot.content_identity
    assert health["freshness"]["current_content_identity"] != snapshot.content_identity
    assert health["freshness"]["is_stale"] is True
    assert health["freshness"]["stale_reason"] == "content_changed_since_reload"


def test_warm_index_manager_requires_explicit_rebuild_on_policy_mismatch(
    tmp_path: Path,
) -> None:
    import json

    from snowiki.search.workspace import RuntimeLexicalPolicyMismatchError

    _, _, warm_index_manager_cls, _, _ = _load_snowiki_modules()
    manifest_path = tmp_path / "index" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "lexical_policy": "korean-mixed-lexical",
                "lexical_policy_version": 1,
            }
        ),
        encoding="utf-8",
    )

    manager = warm_index_manager_cls(tmp_path)

    with pytest.raises(RuntimeLexicalPolicyMismatchError, match="snowiki rebuild"):
        manager.get()


def test_daemon_execute_query_returns_cached_payload_without_relabeling_it(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.search.indexer import SearchDocument, SearchHit

    daemon = SnowikiDaemon(tmp_path, port=0)
    snapshot = SimpleNamespace(blended=object())
    hit = SearchHit(
        document=SearchDocument(
            id="session-1",
            path="normalized/session-1.json",
            kind="session",
            title="Daemon query hit",
            content="daemon query content",
            summary="Daemon query summary.",
            source_type="normalized",
        ),
        score=7.5,
        matched_terms=("daemon", "query"),
    )
    call_log: list[dict[str, object]] = []
    snapshot_metadata = {
        "snapshot_owner": "daemon.warm_indexes",
        "loaded_at": "2026-04-14T00:00:00Z",
        "runtime_generation": 4,
        "lexical_policy": "legacy-lexical",
        "lexical_policy_version": 1,
        "content_identity": {
            "normalized": {"latest_mtime_ns": 100, "file_count": 1},
            "compiled": {"latest_mtime_ns": 200, "file_count": 2},
        },
        "current_content_identity": {
            "normalized": {"latest_mtime_ns": 100, "file_count": 1},
            "compiled": {"latest_mtime_ns": 200, "file_count": 2},
        },
        "is_stale": False,
        "stale_reason": "",
    }

    def fake_get() -> object:
        return snapshot

    def fake_snapshot_metadata(current_snapshot: object) -> object:
        assert current_snapshot is snapshot
        return snapshot_metadata

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append({"index": index, "query": query, "limit": limit})
        return [hit]

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("daemon query should default to known-item lookup")

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("daemon query should not fall back to topical recall")

    monkeypatch.setattr(daemon.warm_indexes, "get", fake_get)
    monkeypatch.setattr(
        daemon.warm_indexes, "snapshot_metadata", fake_snapshot_metadata
    )
    monkeypatch.setattr(
        "snowiki.daemon.server.known_item_lookup", fake_known_item_lookup
    )
    monkeypatch.setattr("snowiki.daemon.server.temporal_recall", fail_temporal_recall)
    monkeypatch.setattr("snowiki.daemon.server.topical_recall", fail_topical_recall)

    request = QueryRequest(operation="known_item_lookup", query="daemon query", limit=3)
    first = daemon.execute_query(request)
    second = daemon.execute_query(request)

    assert first is second
    assert first == {
        "ok": True,
        "cached": False,
        "operation": "known_item_lookup",
        "query": "daemon query",
        "limit": 3,
        "strategy": "known_item_lookup",
        "diagnostics": {
            "snapshot": snapshot_metadata,
            "cache": {
                "owner": "daemon.response_cache",
                "kind": "ttl_response_cache",
                "ttl_seconds": 30.0,
            },
        },
        "hits": [
            {
                "path": "normalized/session-1.json",
                "title": "Daemon query hit",
                "kind": "session",
                "score": 7.5,
                "matched_terms": ["daemon", "query"],
            }
        ],
    }
    assert call_log == [
        {"index": snapshot.blended, "query": "daemon query", "limit": 3}
    ]


def test_daemon_recall_operation_mirrors_cli_truth_known_item_strategy(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.search.indexer import SearchDocument, SearchHit

    daemon = SnowikiDaemon(tmp_path, port=0)
    snapshot = SimpleNamespace(blended=object())
    hit = SearchHit(
        document=SearchDocument(
            id="session-known-item",
            path="normalized/session-known-item.json",
            kind="session",
            title="Daemon known item hit",
            content="daemon known item content",
            summary="Daemon known item summary.",
            source_type="normalized",
        ),
        score=4.5,
        matched_terms=("known", "item"),
    )
    snapshot_metadata = {
        "snapshot_owner": "daemon.warm_indexes",
        "loaded_at": "2026-04-14T00:00:00Z",
        "runtime_generation": 4,
        "lexical_policy": "legacy-lexical",
        "lexical_policy_version": 1,
        "content_identity": {
            "normalized": {"latest_mtime_ns": 100, "file_count": 1},
            "compiled": {"latest_mtime_ns": 200, "file_count": 2},
        },
        "current_content_identity": {
            "normalized": {"latest_mtime_ns": 100, "file_count": 1},
            "compiled": {"latest_mtime_ns": 200, "file_count": 2},
        },
        "is_stale": False,
        "stale_reason": "",
    }
    call_log: list[dict[str, object]] = []

    def fake_get() -> object:
        return snapshot

    def fake_snapshot_metadata(current_snapshot: object) -> object:
        assert current_snapshot is snapshot
        return snapshot_metadata

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "known_item_lookup", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError(
            "daemon recall parity should not use temporal routing here"
        )

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("daemon recall parity should not fall back to topic here")

    monkeypatch.setattr(daemon.warm_indexes, "get", fake_get)
    monkeypatch.setattr(
        daemon.warm_indexes, "snapshot_metadata", fake_snapshot_metadata
    )
    monkeypatch.setattr(
        "snowiki.daemon.server.known_item_lookup", fake_known_item_lookup
    )
    monkeypatch.setattr("snowiki.daemon.server.temporal_recall", fail_temporal_recall)
    monkeypatch.setattr("snowiki.daemon.server.topical_recall", fail_topical_recall)

    result = daemon.execute_query(
        QueryRequest(operation="recall", query="known item", limit=3)
    )

    assert result == {
        "ok": True,
        "cached": False,
        "operation": "recall",
        "query": "known item",
        "limit": 3,
        "strategy": "known_item",
        "diagnostics": {
            "snapshot": snapshot_metadata,
            "cache": {
                "owner": "daemon.response_cache",
                "kind": "ttl_response_cache",
                "ttl_seconds": 30.0,
            },
        },
        "hits": [
            {
                "path": "normalized/session-known-item.json",
                "title": "Daemon known item hit",
                "kind": "session",
                "score": 4.5,
                "matched_terms": ["known", "item"],
            }
        ],
    }
    assert call_log == [
        {
            "fn": "known_item_lookup",
            "index": snapshot.blended,
            "query": "known item",
            "limit": 3,
        }
    ]
