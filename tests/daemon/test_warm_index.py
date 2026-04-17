from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast


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


def _content_identity(
    *,
    normalized_mtime_ns: int,
    normalized_file_count: int,
    compiled_mtime_ns: int,
    compiled_file_count: int,
    tokenizer_name: str = "regex_v1",
) -> dict[str, object]:
    family = "kiwi" if tokenizer_name.startswith("kiwi_") else "regex"
    return {
        "normalized": {
            "latest_mtime_ns": normalized_mtime_ns,
            "file_count": normalized_file_count,
        },
        "compiled": {
            "latest_mtime_ns": compiled_mtime_ns,
            "file_count": compiled_file_count,
        },
        "tokenizer": {"name": tokenizer_name, "family": family, "version": 1},
    }


def _daemon_cache_key(*, request: Any, content_identity: dict[str, object]) -> str:
    return json.dumps(
        {
            "request": {
                "operation": request.operation,
                "query": request.query,
                "limit": request.limit,
            },
            "content_identity": content_identity,
        },
        sort_keys=True,
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
    assert result["event"] == "ingest"
    assert result["reason"] == "new normalized record"
    assert result["triggered_at"].endswith("Z")
    assert result["owners"] == {
        "cache": "daemon.response_cache",
        "snapshot": "daemon.warm_indexes",
    }
    assert result["freshness"]["snapshot_owner"] == "daemon.warm_indexes"
    assert result["freshness"]["runtime_generation"] == second_snapshot.generation
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
    assert health["freshness"]["snapshot_owner"] == "daemon.warm_indexes"
    assert health["freshness"]["runtime_generation"] == snapshot.generation
    assert health["freshness"]["content_identity"] == snapshot.content_identity
    assert health["freshness"]["current_content_identity"] != snapshot.content_identity
    assert health["freshness"]["is_stale"] is True
    assert health["freshness"]["stale_reason"] == "content_changed_since_reload"


def test_warm_index_manager_treats_tokenizer_only_flip_as_stale(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.warm_index import WarmIndexManager

    tokenizer_holder = {"value": "regex_v1"}
    build_log: list[str] = []

    class FakeCompiler:
        def __init__(self, root: Path) -> None:
            self.root = root

        def load_normalized_records(self) -> list[dict[str, object]]:
            return []

        def build_pages(
            self, records: list[dict[str, object]]
        ) -> list[dict[str, object]]:
            assert records == []
            return []

    def fake_current_runtime_tokenizer_name() -> str:
        return tokenizer_holder["value"]

    def fake_content_freshness_identity(
        root: Path, *, tokenizer_name: str | None = None
    ) -> dict[str, object]:
        assert root == tmp_path
        return _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=1,
            tokenizer_name=tokenizer_name or tokenizer_holder["value"],
        )

    def fake_create_tokenizer(name: str) -> object:
        return SimpleNamespace(name=name)

    def fake_from_records_and_pages(
        *,
        records: list[dict[str, object]],
        pages: list[dict[str, object]],
        tokenizer: object,
    ) -> object:
        assert records == []
        assert pages == []
        build_log.append(cast(Any, tokenizer).name)
        return SimpleNamespace(
            lexical=SimpleNamespace(),
            wiki=SimpleNamespace(),
            index=SimpleNamespace(size=0),
            records_indexed=0,
            pages_indexed=0,
        )

    monkeypatch.setattr(
        "snowiki.daemon.warm_index.current_runtime_tokenizer_name",
        fake_current_runtime_tokenizer_name,
    )
    monkeypatch.setattr(
        "snowiki.daemon.warm_index.content_freshness_identity",
        fake_content_freshness_identity,
    )
    monkeypatch.setattr(
        "snowiki.daemon.warm_index.create_tokenizer",
        fake_create_tokenizer,
    )
    monkeypatch.setattr(
        "snowiki.daemon.warm_index.RetrievalService.from_records_and_pages",
        fake_from_records_and_pages,
    )

    manager = WarmIndexManager(
        tmp_path,
        compiler_factory=cast(Any, FakeCompiler),
    )
    first_snapshot = manager.get()
    tokenizer_holder["value"] = "kiwi_nouns_v1"

    freshness_before_reload = manager.snapshot_metadata(first_snapshot)
    refreshed = manager.ensure_fresh_snapshot()

    assert freshness_before_reload["content_identity"]["normalized"] == {
        "latest_mtime_ns": 100,
        "file_count": 1,
    }
    assert freshness_before_reload["content_identity"]["compiled"] == {
        "latest_mtime_ns": 200,
        "file_count": 1,
    }
    assert freshness_before_reload["content_identity"]["tokenizer"] == {
        "name": "regex_v1",
        "family": "regex",
        "version": 1,
    }
    assert freshness_before_reload["current_content_identity"]["normalized"] == {
        "latest_mtime_ns": 100,
        "file_count": 1,
    }
    assert freshness_before_reload["current_content_identity"]["compiled"] == {
        "latest_mtime_ns": 200,
        "file_count": 1,
    }
    assert freshness_before_reload["current_content_identity"]["tokenizer"] == {
        "name": "kiwi_nouns_v1",
        "family": "kiwi",
        "version": 1,
    }
    assert freshness_before_reload["is_stale"] is True
    assert freshness_before_reload["stale_reason"] == "content_changed_since_reload"
    assert refreshed.reloaded is True
    assert refreshed.freshness["is_stale"] is False
    assert refreshed.snapshot.content_identity["tokenizer"] == {
        "name": "kiwi_nouns_v1",
        "family": "kiwi",
        "version": 1,
    }
    assert build_log == ["regex_v1", "kiwi_nouns_v1"]


def test_warm_index_manager_reload_restores_freshness_before_serving(
    tmp_path: Path,
) -> None:
    _, _, warm_index_manager_cls, normalized_storage_cls, known_item_lookup = (
        _load_snowiki_modules()
    )

    storage = normalized_storage_cls(tmp_path)
    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-1",
        payload={
            "metadata": {"title": "First Session"},
            "summary": "Before refresh.",
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

    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-2",
        payload={
            "metadata": {"title": "Second Session"},
            "summary": "After refresh.",
        },
        raw_ref={
            "sha256": "def456",
            "path": "raw/claude/de/f456",
            "size": 42,
            "mtime": "2026-04-08T12:05:00Z",
        },
        recorded_at="2026-04-08T12:05:00Z",
    )

    refreshed = manager.ensure_fresh_snapshot()
    hits = known_item_lookup(refreshed.snapshot.blended, "second session", limit=3)

    assert refreshed.reloaded is True
    assert refreshed.snapshot.generation > first_snapshot.generation
    assert (
        refreshed.freshness["content_identity"] == refreshed.snapshot.content_identity
    )
    assert (
        refreshed.freshness["current_content_identity"]
        == refreshed.snapshot.content_identity
    )
    assert refreshed.freshness["is_stale"] is False
    assert hits
    assert hits[0].document.title == "Second Session"


def test_daemon_execute_query_returns_cached_payload_without_relabeling_it(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.search.indexer import SearchDocument, SearchHit

    daemon = SnowikiDaemon(tmp_path, port=0)
    snapshot = cast(Any, SimpleNamespace(blended=object()))
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
        "content_identity": _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=2,
        ),
        "current_content_identity": _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=2,
        ),
        "is_stale": False,
        "stale_reason": "",
    }

    def fake_get() -> object:
        return snapshot

    def fake_ensure_fresh_snapshot() -> object:
        return SimpleNamespace(
            snapshot=snapshot, freshness=snapshot_metadata, reloaded=False
        )

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
        daemon.warm_indexes, "ensure_fresh_snapshot", fake_ensure_fresh_snapshot
    )
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


def test_daemon_execute_query_invalidates_response_cache_after_refresh_reload(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.daemon.warm_index import FreshSnapshotResult
    from snowiki.search.indexer import SearchDocument, SearchHit

    daemon = SnowikiDaemon(tmp_path, port=0)
    snapshot = cast(Any, SimpleNamespace(blended=object()))
    hit = SearchHit(
        document=SearchDocument(
            id="session-2",
            path="normalized/session-2.json",
            kind="session",
            title="Fresh daemon hit",
            content="fresh daemon content",
            summary="Fresh daemon summary.",
            source_type="normalized",
        ),
        score=5.0,
        matched_terms=("fresh", "daemon"),
    )
    freshness = {
        "snapshot_owner": "daemon.warm_indexes",
        "loaded_at": "2026-04-14T00:00:00Z",
        "runtime_generation": 5,
        "content_identity": _content_identity(
            normalized_mtime_ns=110,
            normalized_file_count=2,
            compiled_mtime_ns=210,
            compiled_file_count=2,
            tokenizer_name="kiwi_nouns_v1",
        ),
        "current_content_identity": _content_identity(
            normalized_mtime_ns=110,
            normalized_file_count=2,
            compiled_mtime_ns=210,
            compiled_file_count=2,
            tokenizer_name="kiwi_nouns_v1",
        ),
        "is_stale": False,
        "stale_reason": "",
    }
    call_log: list[dict[str, object]] = []

    daemon.cache.set(
        _daemon_cache_key(
            request=QueryRequest(
                operation="known_item_lookup", query="daemon query", limit=3
            ),
            content_identity=freshness["content_identity"],
        ),
        {"ok": True, "cached": True},
    )

    def fake_ensure_fresh_snapshot() -> FreshSnapshotResult:
        return FreshSnapshotResult(
            snapshot=snapshot, freshness=freshness, reloaded=True
        )

    def fake_snapshot_metadata(current_snapshot: object) -> object:
        assert current_snapshot is snapshot
        return freshness

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append({"index": index, "query": query, "limit": limit})
        return [hit]

    monkeypatch.setattr(
        daemon.warm_indexes, "ensure_fresh_snapshot", fake_ensure_fresh_snapshot
    )
    monkeypatch.setattr(
        daemon.warm_indexes, "snapshot_metadata", fake_snapshot_metadata
    )
    monkeypatch.setattr(
        "snowiki.daemon.server.known_item_lookup", fake_known_item_lookup
    )

    result = daemon.execute_query(
        QueryRequest(operation="known_item_lookup", query="daemon query", limit=3)
    )

    assert (
        daemon.cache.get(
            _daemon_cache_key(
                request=QueryRequest(
                    operation="known_item_lookup", query="daemon query", limit=3
                ),
                content_identity=freshness["content_identity"],
            )
        )
        is result
    )
    assert result["hits"][0]["title"] == "Fresh daemon hit"
    assert result["diagnostics"]["snapshot"] == freshness
    assert call_log == [
        {"index": snapshot.blended, "query": "daemon query", "limit": 3}
    ]


def test_daemon_execute_query_fails_closed_when_refresh_cannot_restore_freshness(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.daemon.warm_index import WarmSnapshotStaleError

    daemon = SnowikiDaemon(tmp_path, port=0)
    freshness = {
        "snapshot_owner": "daemon.warm_indexes",
        "loaded_at": "2026-04-14T00:00:00Z",
        "runtime_generation": 4,
        "content_identity": _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=2,
        ),
        "current_content_identity": _content_identity(
            normalized_mtime_ns=101,
            normalized_file_count=2,
            compiled_mtime_ns=201,
            compiled_file_count=3,
        ),
        "is_stale": True,
        "stale_reason": "content_changed_since_reload",
    }

    daemon.cache.set(
        _daemon_cache_key(
            request=QueryRequest(
                operation="known_item_lookup", query="daemon query", limit=3
            ),
            content_identity=freshness["content_identity"],
        ),
        {"ok": True, "cached": True},
    )

    def fail_refresh() -> None:
        raise WarmSnapshotStaleError(freshness)

    monkeypatch.setattr(daemon.warm_indexes, "ensure_fresh_snapshot", fail_refresh)

    try:
        daemon.execute_query(
            QueryRequest(operation="known_item_lookup", query="daemon query", limit=3)
        )
    except WarmSnapshotStaleError as exc:
        assert exc.freshness == freshness
    else:
        raise AssertionError("expected daemon freshness failure")

    assert (
        daemon.cache.get(
            _daemon_cache_key(
                request=QueryRequest(
                    operation="known_item_lookup", query="daemon query", limit=3
                ),
                content_identity=freshness["content_identity"],
            )
        )
        is None
    )


def test_daemon_response_cache_key_tracks_tokenizer_identity(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from snowiki.daemon.server import QueryRequest, SnowikiDaemon
    from snowiki.search.indexer import SearchDocument, SearchHit

    daemon = SnowikiDaemon(tmp_path, port=0)
    snapshot = cast(Any, SimpleNamespace(blended=object()))
    regex_identity = _content_identity(
        normalized_mtime_ns=100,
        normalized_file_count=1,
        compiled_mtime_ns=200,
        compiled_file_count=2,
        tokenizer_name="regex_v1",
    )
    kiwi_identity = _content_identity(
        normalized_mtime_ns=100,
        normalized_file_count=1,
        compiled_mtime_ns=200,
        compiled_file_count=2,
        tokenizer_name="kiwi_nouns_v1",
    )
    freshness = {
        "snapshot_owner": "daemon.warm_indexes",
        "loaded_at": "2026-04-14T00:00:00Z",
        "runtime_generation": 4,
        "content_identity": kiwi_identity,
        "current_content_identity": kiwi_identity,
        "is_stale": False,
        "stale_reason": "",
    }
    hit = SearchHit(
        document=SearchDocument(
            id="session-tokenizer-flip",
            path="normalized/session-tokenizer-flip.json",
            kind="session",
            title="Tokenizer-specific hit",
            content="fresh tokenizer content",
            summary="Fresh hit after tokenizer flip.",
            source_type="normalized",
        ),
        score=6.0,
        matched_terms=("tokenizer", "flip"),
    )
    request = QueryRequest(
        operation="known_item_lookup", query="tokenizer flip", limit=3
    )
    call_log: list[dict[str, object]] = []

    daemon.cache.set(
        _daemon_cache_key(request=request, content_identity=regex_identity),
        {"ok": True, "cached": True, "hits": []},
    )

    def fake_ensure_fresh_snapshot() -> object:
        return SimpleNamespace(snapshot=snapshot, freshness=freshness, reloaded=False)

    def fake_snapshot_metadata(current_snapshot: object) -> object:
        assert current_snapshot is snapshot
        return freshness

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append({"index": index, "query": query, "limit": limit})
        return [hit]

    monkeypatch.setattr(
        daemon.warm_indexes, "ensure_fresh_snapshot", fake_ensure_fresh_snapshot
    )
    monkeypatch.setattr(
        daemon.warm_indexes, "snapshot_metadata", fake_snapshot_metadata
    )
    monkeypatch.setattr(
        "snowiki.daemon.server.known_item_lookup", fake_known_item_lookup
    )

    result = daemon.execute_query(request)

    assert result["hits"][0]["title"] == "Tokenizer-specific hit"
    assert daemon.cache.get(
        _daemon_cache_key(request=request, content_identity=regex_identity)
    ) == {
        "ok": True,
        "cached": True,
        "hits": [],
    }
    assert (
        daemon.cache.get(
            _daemon_cache_key(request=request, content_identity=kiwi_identity)
        )
        is result
    )
    assert call_log == [
        {"index": snapshot.blended, "query": "tokenizer flip", "limit": 3}
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
        "content_identity": _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=2,
        ),
        "current_content_identity": _content_identity(
            normalized_mtime_ns=100,
            normalized_file_count=1,
            compiled_mtime_ns=200,
            compiled_file_count=2,
        ),
        "is_stale": False,
        "stale_reason": "",
    }
    call_log: list[dict[str, object]] = []

    def fake_get() -> object:
        return snapshot

    def fake_ensure_fresh_snapshot() -> object:
        return SimpleNamespace(
            snapshot=snapshot, freshness=snapshot_metadata, reloaded=False
        )

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
        daemon.warm_indexes, "ensure_fresh_snapshot", fake_ensure_fresh_snapshot
    )
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
