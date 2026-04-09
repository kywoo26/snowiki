from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

run = importlib.import_module("snowiki.cli.commands.mcp").run

THIS_DIR = Path(__file__).resolve().parents[1] / "retrieval"
CONFTST_PATH = THIS_DIR / "conftest.py"
SPEC = importlib.util.spec_from_file_location("retrieval_conftest", CONFTST_PATH)
assert SPEC is not None and SPEC.loader is not None
retrieval_fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retrieval_fixtures)


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


class MCPSearchSmokeTest(unittest.TestCase):
    def test_stdio_smoke_search_recall_and_resource_reads_match_core(self) -> None:
        search = retrieval_fixtures.load_search_api()
        records = retrieval_fixtures.normalized_records()
        pages = tuple(retrieval_fixtures.compiled_pages()) + (
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
                            "arguments": {
                                "path": "compiled/topics/korean-retrieval.md"
                            },
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
                            "arguments": {
                                "path": "compiled/topics/korean-retrieval.md"
                            },
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

        self.assertEqual(exit_code, 0)
        responses = {
            response["id"]: response for response in decode_messages(stdout.getvalue())
        }

        listed_tools = [tool["name"] for tool in responses[2]["result"]["tools"]]
        self.assertEqual(
            listed_tools, ["get_page", "recall", "resolve_links", "search"]
        )

        blended_index = search.build_blended_index(
            search.build_lexical_index(records).documents,
            search.build_wiki_index(pages).documents,
        )
        expected_search_paths = [
            hit.document.path
            for hit in blended_index.search(
                "basic Claude fixture 위치 알려줘.", limit=3
            )
        ]
        returned_search_paths = [
            hit["path"] for hit in responses[3]["result"]["structuredContent"]["hits"]
        ]
        self.assertEqual(returned_search_paths, expected_search_paths)

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
        self.assertEqual(returned_recall_paths, expected_recall_paths)

        self.assertEqual(
            responses[5]["result"]["structuredContent"]["path"],
            "compiled/topics/korean-retrieval.md",
        )
        resolved_links = responses[6]["result"]["structuredContent"]["links"]
        self.assertTrue(
            any(
                link["resolved_path"]
                == "compiled/wiki/search/mixed-language-overview.md"
                for link in resolved_links
            )
        )

        listed_resources = [
            resource["uri"] for resource in responses[7]["result"]["resources"]
        ]
        self.assertIn("graph://current", listed_resources)
        self.assertIn("topic://korean-retrieval", listed_resources)
        self.assertIn("session://session-yesterday-korean-english", listed_resources)

        session_payload = json.loads(responses[8]["result"]["contents"][0]["text"])
        self.assertEqual(session_payload["id"], "session-yesterday-korean-english")

        graph_payload = json.loads(responses[9]["result"]["contents"][0]["text"])
        self.assertTrue(graph_payload["nodes"])
        self.assertTrue(graph_payload["edges"])


if __name__ == "__main__":
    unittest.main()
