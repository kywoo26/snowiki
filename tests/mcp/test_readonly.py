from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

create_server = importlib.import_module("snowiki.mcp").create_server


class ReadOnlyMCPTest(unittest.TestCase):
    def test_only_read_tools_are_exposed_and_write_tools_are_rejected(self) -> None:
        server = create_server()

        tool_names = [tool["name"] for tool in server.list_tools()]
        self.assertEqual(tool_names, ["get_page", "recall", "resolve_links", "search"])
        self.assertNotIn("ingest", tool_names)
        self.assertNotIn("edit", tool_names)

        for blocked_name in ("ingest", "edit", "sync"):
            with self.subTest(blocked_name=blocked_name):
                result = server.call_tool(blocked_name, {})
                self.assertTrue(result["isError"])
                self.assertIn("read-only", result["content"][0]["text"])

    def test_only_read_resources_are_listed(self) -> None:
        server = create_server(
            session_records=[
                {"id": "session-1", "path": "sessions/1.json", "title": "Session 1"}
            ],
            compiled_pages=[
                {"path": "compiled/topics/topic-one.md", "title": "Topic One"}
            ],
        )

        resource_uris = [resource["uri"] for resource in server.list_resources()]
        self.assertEqual(
            resource_uris,
            ["graph://current", "session://session-1", "topic://topic-one"],
        )
        self.assertTrue(all("://" in uri for uri in resource_uris))


if __name__ == "__main__":
    unittest.main()
