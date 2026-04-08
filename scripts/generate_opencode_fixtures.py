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
    """
    )
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

    open(corrupted_dir / "empty.db", "w").close()

    with open(corrupted_dir / "not_sqlite.db", "w") as f:
        f.write("This is not a SQLite database file\n")

    with open(corrupted_dir / "truncated.db", "wb") as f:
        f.write(b"SQLite format 3\x00")

    print(f"Generated OMO fixtures in {fixtures_dir}")


if __name__ == "__main__":
    create_opencode_fixtures()
