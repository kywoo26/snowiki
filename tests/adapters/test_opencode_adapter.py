from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

load_opencode_session = importlib.import_module(
    "snowiki.adapters.opencode"
).load_opencode_session


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        create table project (
            id text primary key,
            worktree text not null,
            vcs text,
            name text,
            icon_url text,
            icon_color text,
            time_created integer not null,
            time_updated integer not null,
            time_initialized integer,
            sandboxes text not null,
            commands text
        );
        create table workspace (
            id text primary key,
            branch text,
            project_id text not null,
            type text not null,
            name text,
            directory text,
            extra text
        );
        create table session (
            id text primary key,
            project_id text not null,
            parent_id text,
            slug text not null,
            directory text not null,
            title text not null,
            version text not null,
            share_url text,
            summary_additions integer,
            summary_deletions integer,
            summary_files integer,
            summary_diffs text,
            revert text,
            permission text,
            time_created integer not null,
            time_updated integer not null,
            time_compacting integer,
            time_archived integer,
            workspace_id text
        );
        create table message (
            id text primary key,
            session_id text not null,
            time_created integer not null,
            time_updated integer not null,
            data text not null
        );
        create table part (
            id text primary key,
            message_id text not null,
            session_id text not null,
            time_created integer not null,
            time_updated integer not null,
            data text not null
        );
        create table todo (
            session_id text not null,
            content text not null,
            status text not null,
            priority text not null,
            position integer not null,
            time_created integer not null,
            time_updated integer not null,
            primary key (session_id, position)
        );
        """
    )


def _write_fixture_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    _create_schema(connection)
    connection.execute(
        "insert into project values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "proj-1",
            "/workspace/repo",
            "git",
            "repo",
            None,
            None,
            1712577600000,
            1712577605000,
            None,
            "[]",
            '[{"name":"pytest","command":"pytest"}]',
        ),
    )
    connection.execute(
        "insert into workspace values (?, ?, ?, ?, ?, ?, ?)",
        (
            "ws-1",
            "main",
            "proj-1",
            "git",
            "primary",
            "/workspace/repo",
            '{"origin":"local"}',
        ),
    )
    connection.execute(
        "insert into session values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "ses-1",
            "proj-1",
            None,
            "calm-otter",
            "/workspace/repo",
            "OpenCode adapter test",
            "1.3.17",
            None,
            4,
            1,
            2,
            '[{"path":"snowiki/adapters/opencode/__init__.py","change":"modified"}]',
            None,
            '[{"permission":"bash","action":"allow","pattern":"*"}]',
            1712577600000,
            1712577610000,
            None,
            None,
            "ws-1",
        ),
    )
    connection.execute(
        "insert into message values (?, ?, ?, ?, ?)",
        (
            "msg-user",
            "ses-1",
            1712577601000,
            1712577601000,
            '{"role":"user","time":{"created":1712577601000},"system":"Remember canonical schema invariants."}',
        ),
    )
    connection.execute(
        "insert into message values (?, ?, ?, ?, ?)",
        (
            "msg-assistant",
            "ses-1",
            1712577602000,
            1712577603000,
            '{"role":"assistant","time":{"created":1712577602000},"summary":{"diffs":[{"path":"tests/adapters/test_opencode_adapter.py","change":"added"}]},"systemReminder":"Do not skip verification."}',
        ),
    )
    part_rows = [
        (
            "prt-text",
            "msg-user",
            "ses-1",
            1712577601000,
            1712577601000,
            '{"type":"text","text":"Implement the adapter."}',
        ),
        (
            "prt-reasoning",
            "msg-assistant",
            "ses-1",
            1712577602100,
            1712577602150,
            '{"type":"reasoning","text":"Need parser + normalizer + failure handling."}',
        ),
        (
            "prt-tool",
            "msg-assistant",
            "ses-1",
            1712577602200,
            1712577602250,
            '{"type":"tool","tool":"bash","state":{"status":"completed","input":{"command":"pytest"},"output":"2 passed"}}',
        ),
        (
            "prt-patch",
            "msg-assistant",
            "ses-1",
            1712577602300,
            1712577602350,
            '{"type":"patch","hash":"abc123","files":["snowiki/adapters/opencode/parser.py"]}',
        ),
        (
            "prt-agent",
            "msg-assistant",
            "ses-1",
            1712577602400,
            1712577602450,
            '{"type":"agent","agent":"explore","status":"completed","summary":"Found schema"}',
        ),
        (
            "prt-compaction",
            "msg-assistant",
            "ses-1",
            1712577602500,
            1712577602550,
            '{"type":"compaction","summary":"Conversation compacted","messages":12}',
        ),
    ]
    connection.executemany("insert into part values (?, ?, ?, ?, ?, ?)", part_rows)
    connection.execute(
        "insert into todo values (?, ?, ?, ?, ?, ?, ?)",
        (
            "ses-1",
            "Finish adapter",
            "completed",
            "high",
            0,
            1712577602600,
            1712577602650,
        ),
    )
    connection.commit()
    connection.close()


def test_opencode_adapter_maps_session_to_canonical_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _write_fixture_db(db_path)

    result = load_opencode_session("ses-1", db_path=db_path)

    assert result.error is None
    assert result.session is not None
    assert result.session.id == "ses-1"
    assert result.session.source == "opencode"
    assert result.ingest_status.state.value == "normalized"
    assert [message.id for message in result.messages] == ["msg-user", "msg-assistant"]
    assert [part.type for part in result.messages[1].parts] == [
        "reasoning",
        "tool",
        "patch",
        "agent",
        "compaction",
    ]
    tool_part = result.messages[1].parts[1]
    assert tool_part.text == "2 passed"
    assert tool_part.data is not None
    assert tool_part.data["tool"] == "bash"
    assert {event.type for event in result.events} >= {
        "message",
        "todo",
        "diff",
        "system_reminder",
    }
    todo_event = next(event for event in result.events if event.type == "todo")
    assert todo_event.source_metadata is not None
    assert todo_event.source_metadata["content"] == "Finish adapter"
    system_event = next(
        event for event in result.events if event.type == "system_reminder"
    )
    assert system_event.source_metadata is not None
    assert "text" in system_event.source_metadata
