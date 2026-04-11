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
                content = result["content"]
                self.assertIsInstance(content, list)
                assert isinstance(content, list)
                self.assertTrue(content)
                first_item = content[0]
                assert isinstance(first_item, dict)
                first_item_dict = first_item  # type: ignore[assignment]
                text = first_item_dict.get("text")  # type: ignore
                self.assertIsInstance(text, str)
                assert isinstance(text, str)
                self.assertIn("read-only", text)

    def test_only_read_resources_are_listed(self) -> None:
        server = create_server(
            session_records=[
                {"id": "session-1", "path": "sessions/1.json", "title": "Session 1"}
            ],
            compiled_pages=[
                {"path": "compiled/topics/topic-one.md", "title": "Topic One"}
            ],
        )

        resource_uris: list[str] = []
        for resource in server.list_resources():
            uri = resource["uri"]
            self.assertIsInstance(uri, str)
            assert isinstance(uri, str)
            resource_uris.append(uri)
        self.assertEqual(
            resource_uris,
            ["graph://current", "session://session-1", "topic://topic-one"],
        )
        self.assertTrue(all("://" in uri for uri in resource_uris))


if __name__ == "__main__":
    unittest.main()
