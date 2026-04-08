from __future__ import annotations

import importlib

from snowiki.mcp.resources import graph, session, topic
from snowiki.mcp.server import SnowikiReadOnlyFacade


def _facade() -> SnowikiReadOnlyFacade:
    return SnowikiReadOnlyFacade(
        session_records=[
            {
                "id": "session-1",
                "path": "sessions/2026/04/09/session-1.json",
                "title": "Session 1",
            }
        ],
        compiled_pages=[
            {
                "path": "compiled/topics/topic-one.md",
                "title": "Topic One",
                "summary": "First topic.",
                "related": ["compiled/topics/topic-two.md"],
            },
            {
                "path": "compiled/topics/topic-two.md",
                "title": "Topic Two",
                "summary": "Second topic.",
                "related": [],
            },
        ],
    )


def test_resource_modules_delegate_to_facade_methods() -> None:
    facade = _facade()

    assert graph.RESOURCE_URI == "graph://current"
    assert session.RESOURCE_SCHEME == "session://"
    assert topic.RESOURCE_SCHEME == "topic://"

    assert graph.build_resource(facade) == facade.graph_resource()
    assert session.build_resource(facade, "session-1") == facade.session_resource(
        "session-1"
    )
    assert topic.build_resource(facade, "topic-one") == facade.topic_resource(
        "topic-one"
    )


def test_resources_package_is_importable() -> None:
    resources_package = importlib.import_module("snowiki.mcp.resources")

    assert resources_package.__name__ == "snowiki.mcp.resources"
