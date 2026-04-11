#!/usr/bin/env python3
"""Generate OpenCode fixture databases for testing."""

import json
import sqlite3
from pathlib import Path


def create_schema(conn):
    """Create the required OpenCode schema."""
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS project (
            id TEXT PRIMARY KEY,
            worktree TEXT,
            vcs TEXT,
            name TEXT,
            icon_url TEXT,
            icon_color TEXT,
            sandboxes TEXT,
            commands TEXT
        );
        
        CREATE TABLE IF NOT EXISTS session (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            workspace_id TEXT,
            parent_id TEXT,
            slug TEXT,
            directory TEXT,
            title TEXT,
            version TEXT,
            share_url TEXT,
            summary_additions INTEGER,
            summary_deletions INTEGER,
            summary_files INTEGER,
            summary_diffs TEXT,
            permission TEXT,
            time_created INTEGER,
            time_updated INTEGER,
            time_compacting INTEGER,
            time_archived INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS message (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            time_created INTEGER,
            time_updated INTEGER,
            data TEXT
        );
        
        CREATE TABLE IF NOT EXISTS part (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            session_id TEXT,
            time_created INTEGER,
            time_updated INTEGER,
            data TEXT
        );
        
        CREATE TABLE IF NOT EXISTS todo (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            content TEXT,
            status TEXT,
            priority TEXT,
            position INTEGER,
            time_created INTEGER,
            time_updated INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS workspace (
            id TEXT PRIMARY KEY,
            branch TEXT,
            project_id TEXT,
            type TEXT,
            name TEXT,
            directory TEXT,
            extra TEXT
        );
        
        CREATE TABLE IF NOT EXISTS fixture_provenance (
            fixture_id TEXT PRIMARY KEY,
            family TEXT,
            created TEXT,
            updated TEXT,
            sources TEXT
        );
    """
    )


def insert_provenance(cursor, fixture_id, family="opencode_sqlite"):
    """Insert fixture provenance record."""
    now = "2024-04-01T10:00:00Z"
    sources = json.dumps(["synthetic"])
    cursor.execute(
        "INSERT OR REPLACE INTO fixture_provenance VALUES (?, ?, ?, ?, ?)",
        (fixture_id, family, now, now, sources),
    )


def create_basic_data(
    conn,
    fixture_id,
    session_id="session-001",
    include_todos=False,
    include_diffs=False,
    include_reasoning=False,
    include_compaction=False,
):
    """Create basic fixture data with optional features."""
    cursor = conn.cursor()
    now = 1711965600000

    insert_provenance(cursor, fixture_id)

    cursor.execute(
        "INSERT OR REPLACE INTO project VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "project-001",
            "/home/user/project",
            "git",
            "Test Project",
            None,
            None,
            "[]",
            None,
        ),
    )

    cursor.execute(
        "INSERT OR REPLACE INTO workspace VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "ws-001",
            "main",
            "project-001",
            "local",
            "Main Workspace",
            "/home/user/workspace",
            "{}",
        ),
    )

    time_compacting = now + 60000 if include_compaction else None

    cursor.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            "project-001",
            "ws-001",
            None,
            "test-session",
            "/home/user/project",
            "Test Session",
            "1.0",
            None,
            10 if include_diffs else 0,
            5 if include_diffs else 0,
            3 if include_diffs else 0,
            json.dumps({"files": ["test.py"]}) if include_diffs else None,
            None,
            now,
            now + 30000,
            time_compacting,
            None,
        ),
    )

    msg_data = {"role": "user", "content": "Hello from OMO"}
    if include_reasoning:
        msg_data["reasoning"] = "Step-by-step reasoning"

    cursor.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
        ("msg-001", session_id, now + 1000, now + 1000, json.dumps(msg_data)),
    )

    if include_diffs:
        cursor.execute(
            "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
            (
                "part-001",
                "msg-001",
                session_id,
                now + 1000,
                now + 1000,
                json.dumps({"type": "diff", "content": "@@ -1 +1 @@"}),
            ),
        )
    else:
        part_data = {"type": "text", "content": "Hello from OMO"}
        if include_reasoning:
            part_data["reasoning"] = "Detailed reasoning"
        cursor.execute(
            "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
            (
                "part-001",
                "msg-001",
                session_id,
                now + 1000,
                now + 1000,
                json.dumps(part_data),
            ),
        )

    if include_todos:
        cursor.execute(
            "INSERT INTO todo VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "todo-001",
                session_id,
                "Review code",
                "pending",
                "high",
                1,
                now + 2000,
                now + 2000,
            ),
        )

    conn.commit()


def create_provenance_json(path, fixture_type):
    """Create a provenance JSON file for corrupted fixtures."""
    data = {
        "fixture_id": f"corrupt_opencode_{fixture_type}",
        "family": "opencode_sqlite",
        "description": f"Corrupted fixture: {fixture_type}",
        "created": "2024-04-01T10:00:00Z",
        "updated": "2024-04-01T10:00:00Z",
        "sources": ["synthetic"],
    }
    path.write_text(json.dumps(data, indent=2))


def create_opencode_fixtures():
    """Generate all OpenCode fixture databases."""
    fixtures_dir = Path("fixtures/opencode")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    corrupted_dir = Path("fixtures/corrupted/opencode")
    corrupted_dir.mkdir(parents=True, exist_ok=True)
    corrupted_subdir = fixtures_dir / "corrupted"
    corrupted_subdir.mkdir(exist_ok=True)

    fixtures = [
        ("basic.db", "omo_basic", {}),
        ("with_todos.db", "omo_todos", {"include_todos": True}),
        ("with_diffs.db", "omo_diffs", {"include_diffs": True}),
        ("with_reasoning.db", "omo_reasoning", {"include_reasoning": True}),
        ("with_compaction.db", "omo_compaction", {"include_compaction": True}),
    ]

    for filename, fixture_id, kwargs in fixtures:
        conn = sqlite3.connect(fixtures_dir / filename)
        create_schema(conn)
        create_basic_data(
            conn,
            fixture_id,
            session_id=f"session-{fixture_id.replace('omo_', '')}",
            **kwargs,
        )
        conn.close()

    conn = sqlite3.connect(corrupted_dir / "locked.db")
    create_schema(conn)
    create_basic_data(conn, "corrupt_opencode_locked", session_id="session-locked")
    conn.close()
    create_provenance_json(corrupted_dir / "locked.provenance.json", "locked")

    conn = sqlite3.connect(corrupted_dir / "partial_rows.db")
    create_schema(conn)
    cursor = conn.cursor()
    insert_provenance(cursor, "corrupt_opencode_partial_rows")
    cursor.execute(
        "INSERT OR REPLACE INTO project VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "project-001",
            "/home/user/project",
            "git",
            "Test Project",
            None,
            None,
            "[]",
            None,
        ),
    )
    conn.commit()
    conn.close()
    create_provenance_json(
        corrupted_dir / "partial_rows.provenance.json", "partial_rows"
    )

    conn = sqlite3.connect(corrupted_dir / "schema_mismatch.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE wrong_table (id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()
    create_provenance_json(
        corrupted_dir / "schema_mismatch.provenance.json", "schema_mismatch"
    )

    open(corrupted_subdir / "empty.db", "w").close()

    with open(corrupted_subdir / "not_sqlite.db", "w") as f:
        f.write("This is not a SQLite database file\n")

    with open(corrupted_subdir / "truncated.db", "wb") as f:
        f.write(b"SQLite format 3\x00")

    print(f"Generated fixtures in {fixtures_dir} and {corrupted_dir}")


if __name__ == "__main__":
    create_opencode_fixtures()
