from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import Any, cast

from snowiki.cli.commands.mcp import run
from snowiki.mcp.server import SnowikiReadOnlyFacade
from snowiki.search.indexer import SearchDocument, SearchHit


def encode_message(payload: dict[str, object]) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def decode_messages(buffer: bytes) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(buffer):
        separator = buffer.index(b"\r\n\r\n", cursor)
        header = buffer[cursor:separator].decode("ascii")
        content_length = int(header.split(":", 1)[1].strip())
        start = separator + 4
        end = start + content_length
        decoded = cast(dict[str, Any], json.loads(buffer[start:end].decode("utf-8")))
        messages.append(decoded)
        cursor = end
    return messages


def test_stdio_smoke_search_recall_and_resource_reads_match_core(
    search_api_module,
    normalized_records_data,
    compiled_pages_data,
) -> None:
    search = search_api_module
    records = normalized_records_data
    pages = compiled_pages_data + (
        {
            "id": "topic-korean-retrieval",
            "path": "compiled/topics/korean-retrieval.md",
            "title": "Korean retrieval",
            "summary": "Topic page for Korean retrieval work.",
            "body": "See [[Mixed-language lexical retrieval overview]] for the blended search design.",
            "related": ["compiled/wiki/search/mixed-language-overview.md"],
            "updated_at": "2026-04-08T12:00:00Z",
        },
    )
    reference_time = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)

    requests = b"".join(
        (
            encode_message(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
            ),
            encode_message(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "search",
                        "arguments": {
                            "query": "basic Claude fixture 위치 알려줘.",
                            "limit": 3,
                        },
                    },
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "recall",
                        "arguments": {
                            "query": "What did we work on yesterday for Korean retrieval?",
                            "limit": 3,
                            "reference_time": reference_time.isoformat().replace(
                                "+00:00", "Z"
                            ),
                        },
                    },
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "get_page",
                        "arguments": {"path": "compiled/topics/korean-retrieval.md"},
                    },
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "resolve_links",
                        "arguments": {"path": "compiled/topics/korean-retrieval.md"},
                    },
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "resources/list",
                    "params": {},
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "resources/read",
                    "params": {"uri": "session://session-yesterday-korean-english"},
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "resources/read",
                    "params": {"uri": "graph://current"},
                }
            ),
        )
    )

    stdin = io.BytesIO(requests)
    stdout = io.BytesIO()
    exit_code = run(
        ["serve", "--stdio"],
        session_records=records,
        compiled_pages=pages,
        reference_time=reference_time,
        input_stream=stdin,
        output_stream=stdout,
    )

    assert exit_code == 0
    responses = {
        response["id"]: response for response in decode_messages(stdout.getvalue())
    }
    assert sorted(responses) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert all(response["jsonrpc"] == "2.0" for response in responses.values())
    assert all(
        response["id"] == request_id for request_id, response in responses.items()
    )

    initialize_result = responses[1]["result"]
    assert initialize_result["protocolVersion"] == "2025-03-26"
    assert initialize_result["serverInfo"] == {
        "name": "snowiki-readonly",
        "version": "0.1.0",
    }
    assert initialize_result["capabilities"] == {
        "resources": {"listChanged": False, "subscribe": False},
        "tools": {"listChanged": False},
    }

    listed_tools = [tool["name"] for tool in responses[2]["result"]["tools"]]
    assert listed_tools == ["get_page", "recall", "resolve_links", "search"]

    blended_index = search.build_blended_index(
        search.build_lexical_index(records).documents,
        search.build_wiki_index(pages).documents,
    )
    expected_search_paths = [
        hit.document.path
        for hit in blended_index.search("basic Claude fixture 위치 알려줘.", limit=3)
    ]
    returned_search_paths = [
        hit["path"] for hit in responses[3]["result"]["structuredContent"]["hits"]
    ]
    assert returned_search_paths == expected_search_paths
    assert (
        responses[3]["result"]["structuredContent"]["query"]
        == "basic Claude fixture 위치 알려줘."
    )
    assert responses[3]["result"]["structuredContent"]["limit"] == 3
    assert (
        json.loads(responses[3]["result"]["content"][0]["text"])
        == responses[3]["result"]["structuredContent"]
    )

    expected_recall_paths = [
        hit.document.path
        for hit in search.temporal_recall(
            blended_index,
            "What did we work on yesterday for Korean retrieval?",
            limit=3,
            reference_time=reference_time,
        )
    ]
    returned_recall_paths = [
        hit["path"] for hit in responses[4]["result"]["structuredContent"]["hits"]
    ]
    assert returned_recall_paths == expected_recall_paths
    assert responses[4]["result"]["structuredContent"]["mode"] == "temporal"
    assert responses[4]["result"]["structuredContent"]["strategy"] == "temporal"
    assert responses[4]["result"]["structuredContent"]["limit"] == 3
    assert (
        json.loads(responses[4]["result"]["content"][0]["text"])
        == responses[4]["result"]["structuredContent"]
    )

    assert (
        responses[5]["result"]["structuredContent"]["path"]
        == "compiled/topics/korean-retrieval.md"
    )
    assert (
        json.loads(responses[5]["result"]["content"][0]["text"])
        == responses[5]["result"]["structuredContent"]
    )
    resolved_links = responses[6]["result"]["structuredContent"]["links"]
    assert any(
        link["resolved_path"] == "compiled/wiki/search/mixed-language-overview.md"
        for link in resolved_links
    )
    assert (
        json.loads(responses[6]["result"]["content"][0]["text"])
        == responses[6]["result"]["structuredContent"]
    )

    listed_resources = [
        resource["uri"] for resource in responses[7]["result"]["resources"]
    ]
    assert "graph://current" in listed_resources
    assert "topic://korean-retrieval" in listed_resources
    assert "session://session-yesterday-korean-english" in listed_resources

    session_payload = json.loads(responses[8]["result"]["contents"][0]["text"])
    assert session_payload["id"] == "session-yesterday-korean-english"
    assert responses[8]["result"]["contents"][0]["mimeType"] == "application/json"
    assert (
        responses[8]["result"]["contents"][0]["uri"]
        == "session://session-yesterday-korean-english"
    )

    graph_payload = json.loads(responses[9]["result"]["contents"][0]["text"])
    assert graph_payload["nodes"]
    assert graph_payload["edges"]
    assert responses[9]["result"]["contents"][0]["mimeType"] == "application/json"
    assert responses[9]["result"]["contents"][0]["uri"] == "graph://current"


def test_stdio_bridge_without_injected_project_data_stays_read_only_but_empty() -> None:
    requests = b"".join(
        (
            encode_message(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "search",
                        "arguments": {"query": "korean retrieval", "limit": 3},
                    },
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "resources/read",
                    "params": {"uri": "graph://current"},
                }
            ),
            encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "ingest", "arguments": {}},
                }
            ),
        )
    )

    stdin = io.BytesIO(requests)
    stdout = io.BytesIO()

    exit_code = run(["serve", "--stdio"], input_stream=stdin, output_stream=stdout)

    assert exit_code == 0
    responses = {
        response["id"]: response for response in decode_messages(stdout.getvalue())
    }
    assert sorted(responses) == [1, 2, 3, 4, 5]
    assert all(response["jsonrpc"] == "2.0" for response in responses.values())

    listed_tools = [tool["name"] for tool in responses[2]["result"]["tools"]]
    assert listed_tools == ["get_page", "recall", "resolve_links", "search"]

    search_result = responses[3]["result"]["structuredContent"]
    assert search_result == {"hits": [], "limit": 3, "query": "korean retrieval"}
    assert json.loads(responses[3]["result"]["content"][0]["text"]) == search_result

    graph_result = json.loads(responses[4]["result"]["contents"][0]["text"])
    assert graph_result == {"edges": [], "nodes": []}
    assert responses[4]["result"]["contents"][0]["uri"] == "graph://current"

    readonly_error = responses[5]["result"]
    assert readonly_error["isError"] is True
    assert readonly_error["structuredContent"] == {
        "error": "Write operation `ingest` is not exposed by this read-only MCP facade."
    }


def test_mcp_recall_auto_prefers_known_item_and_reports_cli_strategy(
    monkeypatch: Any,
) -> None:
    facade = cast(Any, SnowikiReadOnlyFacade())
    runtime_index = object()
    facade.index = runtime_index
    hit = SearchHit(
        document=SearchDocument(
            id="session-known-item",
            path="normalized/session-known-item.json",
            kind="session",
            title="Known item hit",
            content="known item content",
            summary="Known item summary.",
            source_type="normalized",
        ),
        score=6.75,
        matched_terms=("known", "item"),
    )
    call_log: list[dict[str, object]] = []

    def fake_known_item_lookup(
        index: object, query: str, *, limit: int
    ) -> list[SearchHit]:
        call_log.append(
            {"fn": "known_item_lookup", "index": index, "query": query, "limit": limit}
        )
        return [hit]

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("known-item MCP recall should not use temporal routing")

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("known-item MCP recall should not fall back to topic")

    monkeypatch.setattr("snowiki.mcp.server.known_item_lookup", fake_known_item_lookup)
    monkeypatch.setattr("snowiki.mcp.server.temporal_recall", fail_temporal_recall)
    monkeypatch.setattr("snowiki.mcp.server.topical_recall", fail_topical_recall)

    result = facade.recall("known item", limit=4)

    assert result == {
        "hits": [
            {
                "id": "session-known-item",
                "kind": "session",
                "matched_terms": ["known", "item"],
                "metadata": {},
                "path": "normalized/session-known-item.json",
                "recorded_at": None,
                "score": 6.75,
                "source_type": "normalized",
                "summary": "Known item summary.",
                "title": "Known item hit",
            }
        ],
        "limit": 4,
        "mode": "known_item",
        "query": "known item",
        "strategy": "known_item",
    }
    assert call_log == [
        {
            "fn": "known_item_lookup",
            "index": runtime_index,
            "query": "known item",
            "limit": 4,
        },
    ]


def test_mcp_recall_auto_routes_iso_dates_to_date_strategy() -> None:
    facade = cast(Any, SnowikiReadOnlyFacade())
    call_log: list[dict[str, object]] = []
    hit = SearchHit(
        document=SearchDocument(
            id="session-date-window",
            path="normalized/session-date-window.json",
            kind="session",
            title="Date window hit",
            content="date window content",
            summary="Date-window summary.",
            source_type="normalized",
        ),
        score=2.0,
        matched_terms=("2026-04-08",),
    )

    class FakeIndex:
        def search(
            self,
            query: str,
            *,
            limit: int,
            recorded_after: object,
            recorded_before: object,
        ) -> list[SearchHit]:
            call_log.append(
                {
                    "query": query,
                    "limit": limit,
                    "recorded_after": recorded_after,
                    "recorded_before": recorded_before,
                }
            )
            return [hit]

    facade.index = FakeIndex()

    result = facade.recall("2026-04-08", limit=2)

    assert result["mode"] == "date"
    assert result["strategy"] == "date"
    assert result["limit"] == 2
    assert result["query"] == "2026-04-08"
    returned_hits = cast(list[dict[str, object]], result["hits"])
    assert [returned_hit["path"] for returned_hit in returned_hits] == [
        "normalized/session-date-window.json"
    ]
    assert call_log[0]["query"] == "2026-04-08"
    assert call_log[0]["limit"] == 2


def test_mcp_search_stays_direct_and_does_not_apply_recall_auto_routing(
    monkeypatch: Any,
) -> None:
    facade = cast(Any, SnowikiReadOnlyFacade())
    call_log: list[dict[str, object]] = []
    hit = SearchHit(
        document=SearchDocument(
            id="session-search",
            path="normalized/session-search.json",
            kind="session",
            title="Direct search hit",
            content="search content",
            summary="Search summary.",
            source_type="normalized",
        ),
        score=1.5,
        matched_terms=("yesterday",),
    )

    def fail_known_item_lookup(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("MCP search should not call recall strategy layers")

    def fail_temporal_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("MCP search should remain a direct search tool")

    def fail_topical_recall(*_args: object, **_kwargs: object) -> list[SearchHit]:
        raise AssertionError("MCP search should not reuse topic recall")

    class FakeIndex:
        def search(self, query: str, *, limit: int) -> list[SearchHit]:
            call_log.append({"query": query, "limit": limit})
            return [hit]

    facade.index = FakeIndex()
    monkeypatch.setattr("snowiki.mcp.server.known_item_lookup", fail_known_item_lookup)
    monkeypatch.setattr("snowiki.mcp.server.temporal_recall", fail_temporal_recall)
    monkeypatch.setattr("snowiki.mcp.server.topical_recall", fail_topical_recall)

    result = facade.search("yesterday", limit=3)

    assert result == {
        "hits": [
            {
                "id": "session-search",
                "kind": "session",
                "matched_terms": ["yesterday"],
                "metadata": {},
                "path": "normalized/session-search.json",
                "recorded_at": None,
                "score": 1.5,
                "source_type": "normalized",
                "summary": "Search summary.",
                "title": "Direct search hit",
            }
        ],
        "limit": 3,
        "query": "yesterday",
    }
    assert call_log == [{"query": "yesterday", "limit": 3}]
