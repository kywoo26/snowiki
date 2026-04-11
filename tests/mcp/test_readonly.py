from __future__ import annotations

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
        content = result["content"]
        assert isinstance(content, list)
        assert content
        first_item = content[0]
        assert isinstance(first_item, dict)
        text = first_item.get("text")
        assert isinstance(text, str)
        assert "read-only" in text


def test_only_read_resources_are_listed() -> None:
    server = create_server(
        session_records=[
            {"id": "session-1", "path": "sessions/1.json", "title": "Session 1"}
        ],
        compiled_pages=[{"path": "compiled/topics/topic-one.md", "title": "Topic One"}],
    )

    resource_uris: list[str] = []
    for resource in server.list_resources():
        uri = resource["uri"]
        assert isinstance(uri, str)
        resource_uris.append(uri)
    assert resource_uris == [
        "graph://current",
        "session://session-1",
        "topic://topic-one",
    ]
    assert all("://" in uri for uri in resource_uris)
