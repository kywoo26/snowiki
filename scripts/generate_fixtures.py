#!/usr/bin/env python3
"""Generate fixture files for Snowiki V2 testing.

This script generates:
- Claude JSONL fixtures (valid and corrupted)
- OMO SQLite fixtures (valid and corrupted)
- Benchmark queries and judgments
"""

import json
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path


def create_claude_fixtures():
    """Generate Claude JSONL fixtures."""
    fixtures_dir = Path("fixtures/claude")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    corrupted_dir = fixtures_dir / "corrupted"
    corrupted_dir.mkdir(exist_ok=True)

    # Basic valid session
    basic = [
        {
            "record_type": "session_start",
            "session_id": "basic-session-001",
            "timestamp": "2026-04-01T10:00:00Z",
            "project_path": "/home/user/project",
        },
        {
            "record_type": "message",
            "message_id": "msg-001",
            "session_id": "basic-session-001",
            "timestamp": "2026-04-01T10:00:01Z",
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, can you help me with Python?"}
            ],
        },
        {
            "record_type": "message",
            "message_id": "msg-002",
            "session_id": "basic-session-001",
            "timestamp": "2026-04-01T10:00:05Z",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Of course! I'd be happy to help with Python. What do you need assistance with?",
                }
            ],
        },
        {
            "record_type": "session_end",
            "session_id": "basic-session-001",
            "timestamp": "2026-04-01T10:05:00Z",
        },
    ]

    with open(fixtures_dir / "basic.jsonl", "w") as f:
        for record in basic:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # With tools
    with_tools = [
        {
            "record_type": "session_start",
            "session_id": "tools-session-001",
            "timestamp": "2026-04-01T11:00:00Z",
        },
        {
            "record_type": "message",
            "message_id": "msg-101",
            "session_id": "tools-session-001",
            "timestamp": "2026-04-01T11:00:01Z",
            "role": "user",
            "content": [{"type": "text", "text": "List files in current directory"}],
        },
        {
            "record_type": "tool_use",
            "tool_use_id": "tool-001",
            "message_id": "msg-102",
            "session_id": "tools-session-001",
            "timestamp": "2026-04-01T11:00:02Z",
            "name": "bash",
            "input": {"command": "ls -la", "description": "List files"},
        },
        {
            "record_type": "tool_result",
            "tool_use_id": "tool-001",
            "session_id": "tools-session-001",
            "timestamp": "2026-04-01T11:00:03Z",
            "content": [
                {
                    "type": "text",
                    "text": "total 32\ndrwxr-xr-x 5 user user 4096 Apr 1 10:00 .\n...",
                }
            ],
        },
        {
            "record_type": "session_end",
            "session_id": "tools-session-001",
            "timestamp": "2026-04-01T11:01:00Z",
        },
    ]

    with open(fixtures_dir / "with_tools.jsonl", "w") as f:
        for record in with_tools:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Corrupted: malformed JSON
    with open(corrupted_dir / "malformed_json.jsonl", "w") as f:
        f.write(
            '{"record_type": "session_start", "session_id": "broken"\n'
        )  # Missing closing brace
        f.write("this is not json at all\n")

    # Corrupted: missing fields
    with open(corrupted_dir / "missing_fields.jsonl", "w") as f:
        f.write(
            json.dumps({"record_type": "message"}) + "\n"
        )  # Missing required fields

    print(f"Created Claude fixtures in {fixtures_dir}")


def create_opencode_fixtures():
    """Generate OMO SQLite fixtures."""
    fixtures_dir = Path("fixtures/opencode")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    corrupted_dir = fixtures_dir / "corrupted"
    corrupted_dir.mkdir(exist_ok=True)

    # Basic valid database
    conn = sqlite3.connect(fixtures_dir / "basic.db")
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            project_path TEXT
        );

        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            created_at TIMESTAMP,
            role TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE parts (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            type TEXT,
            content TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        );
    """)

    # Insert sample data
    cursor.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?)",
        (
            "session-001",
            "2026-04-01T10:00:00Z",
            "2026-04-01T10:05:00Z",
            "/home/user/project",
        ),
    )
    cursor.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?)",
        ("msg-001", "session-001", "2026-04-01T10:00:01Z", "user"),
    )
    cursor.execute(
        "INSERT INTO parts VALUES (?, ?, ?, ?)",
        ("part-001", "msg-001", "text", "Hello from OMO"),
    )

    conn.commit()
    conn.close()

    # Corrupted: empty file
    open(corrupted_dir / "empty.db", "w").close()

    print(f"Created OMO fixtures in {fixtures_dir}")


def create_benchmarks():
    """Generate benchmark queries and judgments."""
    benchmarks_dir = Path("benchmarks")
    benchmarks_dir.mkdir(exist_ok=True)

    # Korean queries
    ko_queries = [
        {"id": "ko-001", "text": "QMD 한글 문제", "type": "known_item"},
        {"id": "ko-002", "text": "Claude adapter 구현", "type": "topical"},
        {"id": "ko-003", "text": "어제 작업 내용", "type": "temporal"},
    ]

    # English queries
    en_queries = [
        {"id": "en-001", "text": "schema definition", "type": "known_item"},
        {"id": "en-002", "text": "storage zones", "type": "topical"},
        {"id": "en-003", "text": "yesterday sessions", "type": "temporal"},
    ]

    # Mixed queries
    mixed_queries = [
        {"id": "mixed-001", "text": "OMO adapter 테스트", "type": "known_item"},
        {"id": "mixed-002", "text": "bilingual search 구현", "type": "topical"},
    ]

    queries = {
        "korean": ko_queries,
        "english": en_queries,
        "mixed": mixed_queries,
        "metadata": {
            "created": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
        },
    }

    with open(benchmarks_dir / "queries.json", "w") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    # Judgments (relevance labels)
    judgments = {
        "ko-001": {"relevant_docs": ["doc-001", "doc-002"], "score": 1.0},
        "en-001": {"relevant_docs": ["doc-003"], "score": 1.0},
        "mixed-001": {"relevant_docs": ["doc-004", "doc-005"], "score": 0.8},
    }

    with open(benchmarks_dir / "judgments.json", "w") as f:
        json.dump(judgments, f, indent=2)

    print(f"Created benchmarks in {benchmarks_dir}")


def main():
    """Generate all fixtures."""
    print("Generating Snowiki V2 fixtures...")
    create_claude_fixtures()
    create_opencode_fixtures()
    create_benchmarks()
    print("Done!")


if __name__ == "__main__":
    main()
