from __future__ import annotations

from typing import cast

from snowiki.mcp import create_server


def test_only_read_tools_are_exposed_and_write_tools_are_rejected() -> None:
    server = create_server()

    tool_names = [tool["name"] for tool in server.list_tools()]
    assert tool_names == ["get_page", "recall", "resolve_links", "search"]
    assert "ingest" not in tool_names
    assert "edit" not in tool_names

    for blocked_name in ("ingest", "edit", "sync"):
        result = server.call_tool(blocked_name, {})
        assert result["isError"]
        assert result["structuredContent"] == {
            "error": f"Write operation `{blocked_name}` is not exposed by this read-only MCP facade."
        }
        content = result["content"]
        assert isinstance(content, list)
        assert content
        first_item = cast(dict[str, object], content[0])
        assert first_item.get("type") == "text"
        text = first_item.get("text")
        assert isinstance(text, str)
        assert "read-only" in text
        assert blocked_name in text


def test_only_read_resources_are_listed() -> None:
    server = create_server(
        session_records=[
            {"id": "session-1", "path": "sessions/1.json", "title": "Session 1"}
        ],
        compiled_pages=[{"path": "compiled/topics/topic-one.md", "title": "Topic One"}],
    )

    resource_uris: list[str] = []
    for resource in server.list_resources():
        assert resource["mimeType"] == "application/json"
        assert isinstance(resource["name"], str)
        assert resource["name"]
        assert isinstance(resource["description"], str)
        assert resource["description"]
        uri = resource["uri"]
        assert isinstance(uri, str)
        resource_uris.append(uri)
    assert resource_uris == [
        "graph://current",
        "session://session-1",
        "topic://topic-one",
    ]
    assert all("://" in uri for uri in resource_uris)


def test_unknown_resource_reads_return_json_error_payload() -> None:
    server = create_server()

    result = server.read_resource("topic://missing-topic")

    contents = result["contents"]
    assert isinstance(contents, list)
    assert len(contents) == 1
    payload = cast(dict[str, object], contents[0])
    assert payload["mimeType"] == "application/json"
    assert payload["uri"] == "topic://missing-topic"
    text = payload["text"]
    assert isinstance(text, str)
    assert "Unknown topic resource" in text
