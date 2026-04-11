#!/usr/bin/env python3
import sqlite3
from pathlib import Path


def create_opencode_fixtures():
    fixtures_dir = Path("fixtures/opencode")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    corrupted_dir = fixtures_dir / "corrupted"
    corrupted_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect(fixtures_dir / "basic.db")
    cursor = conn.cursor()
    cursor.executescript(
        """
        -- Session table (required)
        CREATE TABLE session (
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
        
        -- Message table (required)
        CREATE TABLE message (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            time_created INTEGER,
            time_updated INTEGER,
            data TEXT
        );
        
        -- Part table (required)
        CREATE TABLE part (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            session_id TEXT,
            time_created INTEGER,
            time_updated INTEGER,
            data TEXT
        );
        
        -- Project table (required)
        CREATE TABLE project (
            id TEXT PRIMARY KEY,
            worktree TEXT,
            vcs TEXT,
            name TEXT,
            icon_url TEXT,
            icon_color TEXT,
            sandboxes TEXT,
            commands TEXT
        );
        
        -- Todo table (required)
        CREATE TABLE todo (
            session_id TEXT,
            content TEXT,
            status TEXT,
            priority TEXT,
            position INTEGER,
            time_created INTEGER,
            time_updated INTEGER
        );
        
        -- Workspace table (required)
        CREATE TABLE workspace (
            id TEXT PRIMARY KEY,
            branch TEXT,
            project_id TEXT,
            type TEXT,
            name TEXT,
            directory TEXT,
            extra TEXT
        );
    """
    )

    # Insert sample data
    cursor.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "session-001",  # id
            "project-001",  # project_id
            None,  # workspace_id
            None,  # parent_id
            "test-session",  # slug
            "/home/user/project",  # directory
            "Test Session",  # title
            "1.0",  # version
            None,  # share_url
            0,  # summary_additions
            0,  # summary_deletions
            0,  # summary_files
            None,  # summary_diffs
            None,  # permission
            1711965600000,  # time_created (2024-04-01T10:00:00Z)
            1711965900000,  # time_updated (2024-04-01T10:05:00Z)
            None,  # time_compacting
            None,  # time_archived
        ),
    )

    cursor.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
        (
            "msg-001",
            "session-001",
            1711965601000,  # time_created
            1711965601000,  # time_updated
            '{"role": "user", "content": "Hello from OMO"}',
        ),
    )

    cursor.execute(
        "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
        (
            "part-001",
            "msg-001",
            "session-001",
            1711965601000,  # time_created
            1711965601000,  # time_updated
            '{"type": "text", "content": "Hello from OMO"}',
        ),
    )

    cursor.execute(
        "INSERT INTO project VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "project-001",
            "/home/user/project",  # worktree
            "git",  # vcs
            "Test Project",  # name
            None,  # icon_url
            None,  # icon_color
            "[]",  # sandboxes
            None,  # commands
        ),
    )

    cursor.execute(
        "INSERT INTO workspace VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "ws-001",
            "main",  # branch
            "project-001",  # project_id
            "local",  # type
            "Main Workspace",  # name
            "/home/user/workspace",  # directory
            "{}",  # extra
        ),
    )

    conn.commit()
    conn.close()

    open(corrupted_dir / "empty.db", "w").close()

    with open(corrupted_dir / "not_sqlite.db", "w") as f:
        f.write("This is not a SQLite database file\n")

    with open(corrupted_dir / "truncated.db", "wb") as f:
        f.write(b"SQLite format 3\x00")

    print(f"Generated OMO fixtures in {fixtures_dir}")


if __name__ == "__main__":
    create_opencode_fixtures()
