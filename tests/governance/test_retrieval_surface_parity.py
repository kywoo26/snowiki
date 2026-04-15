from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import snowiki.search as search_api
from snowiki.daemon.server import QueryRequest, SnowikiDaemon
from snowiki.mcp.server import SnowikiReadOnlyFacade
from snowiki.search import normalize_direct_search_result, normalize_recall_result
from snowiki.search.indexer import SearchDocument, SearchHit

DIRECT_QUERY = "basic Claude fixture 위치 알려줘."
DATE_QUERY = "2026-04-08"
TEMPORAL_QUERY = "What did we work on yesterday for Korean retrieval?"
TOPIC_QUERY = "mixed language retrieval 한국어 영어"


def _build_runtime_snapshot(
    search_api_module,
    normalized_records_data: tuple[dict[str, object], ...],
    compiled_pages_data: tuple[dict[str, object], ...],
) -> SimpleNamespace:
    lexical = search_api_module.build_lexical_index(normalized_records_data)
    wiki = search_api_module.build_wiki_index(compiled_pages_data)
    blended = search_api_module.build_blended_index(lexical.documents, wiki.documents)
    return SimpleNamespace(
        blended=blended,
        index=blended,
        lexical=lexical,
        pages_indexed=len(compiled_pages_data),
        records_indexed=len(normalized_records_data),
        wiki=wiki,
    )


def _build_direct_hit(
    *,
    path: str,
    title: str,
    kind: str = "session",
    score: float = 1.0,
    matched_terms: tuple[str, ...] = (),
    summary: str = "",
) -> SearchHit:
    return SearchHit(
        document=SearchDocument(
            id=path,
            path=path,
            kind=kind,
            title=title,
            content=summary or title,
            summary=summary,
            source_type="normalized" if path.startswith("normalized/") else "compiled",
        ),
        score=score,
        matched_terms=matched_terms,
    )


def _build_query_daemon(root: Path, snapshot: SimpleNamespace) -> SnowikiDaemon:
    daemon = SnowikiDaemon(root, port=0)
    daemon_any = cast(Any, daemon)
    freshness = {
        "snapshot_owner": "daemon.warm_indexes",
        "runtime_generation": 1,
        "content_identity": {"snapshot": id(snapshot)},
        "current_content_identity": {"snapshot": id(snapshot)},
        "is_stale": False,
        "stale_reason": "",
    }
    daemon_any.cache = SimpleNamespace(
        get_or_set=lambda _key, factory: factory(),
        ttl_seconds=30.0,
    )
    daemon_any.warm_indexes = SimpleNamespace(
        get=lambda: snapshot,
        ensure_fresh_snapshot=lambda: SimpleNamespace(
            snapshot=snapshot,
            freshness=freshness,
            reloaded=False,
        ),
        snapshot_metadata=lambda current_snapshot: {
            "snapshot_owner": "daemon.warm_indexes",
            "runtime_generation": 1,
            "content_identity": {"snapshot": id(current_snapshot)},
            "current_content_identity": {"snapshot": id(current_snapshot)},
            "is_stale": False,
            "stale_reason": "",
        },
    )
    return cast(SnowikiDaemon, daemon_any)


def _assert_direct_search_parity(
    cli_result: Mapping[str, object],
    mcp_result: Mapping[str, object],
    daemon_result: Mapping[str, object],
) -> None:
    expected = normalize_direct_search_result(cli_result)
    assert normalize_direct_search_result(mcp_result) == expected
    assert normalize_direct_search_result(daemon_result) == expected


def _assert_recall_parity(
    cli_result: Mapping[str, object],
    mcp_result: Mapping[str, object],
    daemon_result: Mapping[str, object],
) -> None:
    def _project(normalized: Mapping[str, object]) -> dict[str, object]:
        raw_hits = normalized.get("hits")
        hits = raw_hits if isinstance(raw_hits, list) else []
        return {
            "hits": [
                {key: value for key, value in hit.items() if key != "matched_terms"}
                for hit in hits
                if isinstance(hit, Mapping)
            ],
            "strategy": str(normalized.get("strategy") or ""),
        }

    expected = _project(normalize_recall_result(cli_result))
    assert _project(normalize_recall_result(mcp_result)) == expected
    assert _project(normalize_recall_result(daemon_result)) == expected


def _fail_if_called(name: str):
    def _fail(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError(f"{name} should not be used for this route")

    return _fail


def _temporal_recall_with_fixed_reference_time(
    index: Any,
    query: str,
    *,
    limit: int,
    reference_time: object = None,
) -> list[SearchHit]:
    del reference_time
    return search_api.temporal_recall(
        index,
        query,
        limit=limit,
        reference_time=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )


def test_direct_search_parity_across_cli_query_mcp_search_and_daemon_direct_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search_api_module,
    normalized_records_data: tuple[dict[str, object], ...],
    compiled_pages_data: tuple[dict[str, object], ...],
) -> None:
    from snowiki.cli.commands.query import run_query

    snapshot = _build_runtime_snapshot(
        search_api_module, normalized_records_data, compiled_pages_data
    )

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        lambda root: snapshot,
    )

    cli_result = run_query(tmp_path, DIRECT_QUERY, mode="lexical", top_k=1)
    facade = SnowikiReadOnlyFacade(
        session_records=normalized_records_data,
        compiled_pages=compiled_pages_data,
    )
    mcp_result = facade.search(DIRECT_QUERY, limit=1)

    daemon = _build_query_daemon(tmp_path, snapshot)
    daemon_result = daemon.execute_query(
        QueryRequest(operation="topical_recall", query=DIRECT_QUERY, limit=1)
    )

    assert cli_result["query"] == DIRECT_QUERY
    assert mcp_result["query"] == DIRECT_QUERY
    assert daemon_result["query"] == DIRECT_QUERY
    _assert_direct_search_parity(cli_result, mcp_result, daemon_result)


def test_cli_query_stays_direct_lexical_query_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search_api_module,
    normalized_records_data: tuple[dict[str, object], ...],
    compiled_pages_data: tuple[dict[str, object], ...],
) -> None:
    from snowiki.cli.commands.query import run_query

    snapshot = _build_runtime_snapshot(
        search_api_module, normalized_records_data, compiled_pages_data
    )
    hit = _build_direct_hit(
        path="normalized/session-1.json",
        title="Direct lexical hit",
        score=4.25,
        matched_terms=("basic", "fixture"),
        summary="Direct lexical hit summary.",
    )
    call_log: list[dict[str, object]] = []

    def fake_build_retrieval_snapshot(root: Path) -> SimpleNamespace:
        call_log.append({"fn": "build_retrieval_snapshot", "root": root})
        return snapshot

    def fake_topical_recall(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "topical_recall", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    monkeypatch.setattr(
        "snowiki.cli.commands.query.build_retrieval_snapshot",
        fake_build_retrieval_snapshot,
    )
    monkeypatch.setattr(
        "snowiki.cli.commands.query.topical_recall", fake_topical_recall
    )

    result = run_query(tmp_path, DIRECT_QUERY, mode="lexical", top_k=1)

    assert result == {
        "query": DIRECT_QUERY,
        "mode": "lexical",
        "semantic_backend": None,
        "records_indexed": len(normalized_records_data),
        "pages_indexed": len(compiled_pages_data),
        "hits": [
            {
                "id": "normalized/session-1.json",
                "path": "normalized/session-1.json",
                "title": "Direct lexical hit",
                "kind": "session",
                "source_type": "normalized",
                "score": 4.25,
                "matched_terms": ["basic", "fixture"],
                "summary": "Direct lexical hit summary.",
            }
        ],
    }
    assert call_log == [
        {"fn": "build_retrieval_snapshot", "root": tmp_path},
        {
            "fn": "topical_recall",
            "index": snapshot.index,
            "query": DIRECT_QUERY,
            "limit": 1,
        },
    ]


def test_mcp_search_stays_direct_search_only(
    monkeypatch: pytest.MonkeyPatch,
    search_api_module,
    normalized_records_data: tuple[dict[str, object], ...],
    compiled_pages_data: tuple[dict[str, object], ...],
) -> None:
    snapshot = _build_runtime_snapshot(
        search_api_module, normalized_records_data, compiled_pages_data
    )
    facade = SnowikiReadOnlyFacade(
        session_records=normalized_records_data,
        compiled_pages=compiled_pages_data,
    )

    call_log: list[dict[str, object]] = []
    hit = _build_direct_hit(
        path="normalized/session-1.json",
        title="Direct search hit",
        score=1.5,
        matched_terms=("yesterday",),
        summary="Search summary.",
    )

    def fake_search(query: str, *, limit: int) -> list[SearchHit]:
        call_log.append({"query": query, "limit": limit})
        return [hit]

    monkeypatch.setattr(facade, "index", SimpleNamespace(search=fake_search))
    monkeypatch.setattr(
        "snowiki.mcp.server.known_item_lookup", _fail_if_called("known_item_lookup")
    )
    monkeypatch.setattr(
        "snowiki.mcp.server.temporal_recall", _fail_if_called("temporal_recall")
    )
    monkeypatch.setattr(
        "snowiki.mcp.server.topical_recall", _fail_if_called("topical_recall")
    )

    result = facade.search(DIRECT_QUERY, limit=1)

    assert result == {
        "hits": [
            {
                "id": "normalized/session-1.json",
                "kind": "session",
                "matched_terms": ["yesterday"],
                "metadata": {},
                "path": "normalized/session-1.json",
                "recorded_at": None,
                "score": 1.5,
                "source_type": "normalized",
                "summary": "Search summary.",
                "title": "Direct search hit",
            }
        ],
        "limit": 1,
        "query": DIRECT_QUERY,
    }
    assert call_log == [{"query": DIRECT_QUERY, "limit": 1}]
    assert snapshot.index is not None


@pytest.mark.parametrize(
    ("query", "expected_strategy", "patches"),
    [
        pytest.param(
            DATE_QUERY,
            "date",
            {
                "known_item_lookup": _fail_if_called("known_item_lookup"),
                "temporal_recall": _fail_if_called("temporal_recall"),
                "topical_recall": _fail_if_called("topical_recall"),
            },
            id="date",
        ),
        pytest.param(
            TEMPORAL_QUERY,
            "temporal",
            {
                "known_item_lookup": _fail_if_called("known_item_lookup"),
                "temporal_recall": _temporal_recall_with_fixed_reference_time,
                "topical_recall": _fail_if_called("topical_recall"),
            },
            id="temporal",
        ),
        pytest.param(
            DIRECT_QUERY,
            "known_item",
            {
                "temporal_recall": _fail_if_called("temporal_recall"),
                "topical_recall": _fail_if_called("topical_recall"),
            },
            id="known-item",
        ),
        pytest.param(
            TOPIC_QUERY,
            "topic",
            {
                "known_item_lookup": lambda index, query, *, limit: [],
                "temporal_recall": _fail_if_called("temporal_recall"),
            },
            id="topic",
        ),
    ],
)
def test_authoritative_recall_parity_across_cli_recall_mcp_recall_and_daemon_operation_recall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search_api_module,
    normalized_records_data: tuple[dict[str, object], ...],
    compiled_pages_data: tuple[dict[str, object], ...],
    query: str,
    expected_strategy: str,
    patches: dict[str, object],
) -> None:
    from snowiki.cli.commands.recall import run_recall

    snapshot = _build_runtime_snapshot(
        search_api_module, normalized_records_data, compiled_pages_data
    )
    facade = SnowikiReadOnlyFacade(
        session_records=normalized_records_data,
        compiled_pages=compiled_pages_data,
    )
    daemon = _build_query_daemon(tmp_path, snapshot)

    for name, replacement in patches.items():
        monkeypatch.setattr(f"snowiki.cli.commands.recall.{name}", replacement)
        monkeypatch.setattr(f"snowiki.mcp.server.{name}", replacement)
        monkeypatch.setattr(f"snowiki.daemon.server.{name}", replacement)

    monkeypatch.setattr(
        "snowiki.cli.commands.recall.RetrievalService.from_root",
        lambda root: snapshot,
    )

    cli_result = run_recall(tmp_path, query)
    mcp_result = facade.recall(query, limit=10)
    daemon_result = daemon.execute_query(
        QueryRequest(operation="recall", query=query, limit=10)
    )

    assert cli_result["strategy"] == expected_strategy
    assert mcp_result["strategy"] == expected_strategy
    assert daemon_result["strategy"] == expected_strategy
    _assert_recall_parity(cli_result, mcp_result, daemon_result)
