from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .failures import (
    OpenCodePartialSourceError,
    classify_sqlite_error,
)

JsonDict = dict[str, Any]


def _loads_json(raw: str, *, label: str, path: Path) -> JsonDict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenCodePartialSourceError(
            path, f"invalid JSON in {label}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise OpenCodePartialSourceError(path, f"unexpected non-object JSON in {label}")
    return payload


def _from_millis(value: int | None) -> datetime:
    millis = 0 if value is None else value
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


@dataclass(frozen=True, slots=True)
class RawSession:
    id: str
    project_id: str
    workspace_id: str | None
    parent_id: str | None
    slug: str
    directory: str
    title: str
    version: str
    share_url: str | None
    summary_additions: int | None
    summary_deletions: int | None
    summary_files: int | None
    summary_diffs: JsonDict | list[Any] | None
    revert: str | None
    permission: list[Any] | None
    time_created: datetime
    time_updated: datetime
    time_compacting: datetime | None
    time_archived: datetime | None
    row: JsonDict


@dataclass(frozen=True, slots=True)
class RawMessage:
    id: str
    session_id: str
    time_created: datetime
    time_updated: datetime
    data: JsonDict
    row: JsonDict


@dataclass(frozen=True, slots=True)
class RawPart:
    id: str
    message_id: str
    session_id: str
    time_created: datetime
    time_updated: datetime
    data: JsonDict
    row: JsonDict


@dataclass(frozen=True, slots=True)
class RawTodo:
    session_id: str
    content: str
    status: str
    priority: str
    position: int
    time_created: datetime
    time_updated: datetime
    row: JsonDict


@dataclass(frozen=True, slots=True)
class RawProject:
    id: str
    worktree: str
    vcs: str | None
    name: str | None
    icon_url: str | None
    icon_color: str | None
    sandboxes: list[Any]
    commands: list[Any] | JsonDict | None
    row: JsonDict


@dataclass(frozen=True, slots=True)
class RawWorkspace:
    id: str
    branch: str | None
    project_id: str
    type: str
    name: str | None
    directory: str | None
    extra: JsonDict | list[Any] | None
    row: JsonDict


@dataclass(frozen=True, slots=True)
class ParsedSessionSource:
    path: Path
    session: RawSession
    project: RawProject | None
    workspace: RawWorkspace | None
    messages: tuple[RawMessage, ...]
    parts_by_message: dict[str, tuple[RawPart, ...]]
    todos: tuple[RawTodo, ...]


def _optional_json(
    raw: str | None, *, label: str, path: Path
) -> JsonDict | list[Any] | None:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenCodePartialSourceError(
            path, f"invalid JSON in {label}: {exc.msg}"
        ) from exc


def _row_to_dict(row: sqlite3.Row) -> JsonDict:
    return dict(zip(row.keys(), row, strict=True))


def _parse_session(row: sqlite3.Row, *, path: Path) -> RawSession:
    raw = _row_to_dict(row)
    summary_diffs = _optional_json(
        raw.get("summary_diffs"), label="session.summary_diffs", path=path
    )
    permission = _optional_json(
        raw.get("permission"), label="session.permission", path=path
    )
    return RawSession(
        id=str(raw["id"]),
        project_id=str(raw["project_id"]),
        workspace_id=str(raw["workspace_id"])
        if raw.get("workspace_id") is not None
        else None,
        parent_id=str(raw["parent_id"]) if raw.get("parent_id") is not None else None,
        slug=str(raw["slug"]),
        directory=str(raw["directory"]),
        title=str(raw["title"]),
        version=str(raw["version"]),
        share_url=str(raw["share_url"]) if raw.get("share_url") is not None else None,
        summary_additions=raw.get("summary_additions"),
        summary_deletions=raw.get("summary_deletions"),
        summary_files=raw.get("summary_files"),
        summary_diffs=summary_diffs,
        revert=str(raw["revert"]) if raw.get("revert") is not None else None,
        permission=permission if isinstance(permission, list) else None,
        time_created=_from_millis(raw.get("time_created")),
        time_updated=_from_millis(raw.get("time_updated")),
        time_compacting=(
            _from_millis(raw["time_compacting"])
            if raw.get("time_compacting") is not None
            else None
        ),
        time_archived=(
            _from_millis(raw["time_archived"])
            if raw.get("time_archived") is not None
            else None
        ),
        row=raw,
    )


def _parse_project(row: sqlite3.Row, *, path: Path) -> RawProject:
    raw = _row_to_dict(row)
    sandboxes = _optional_json(
        raw.get("sandboxes"), label="project.sandboxes", path=path
    )
    commands = _optional_json(raw.get("commands"), label="project.commands", path=path)
    return RawProject(
        id=str(raw["id"]),
        worktree=str(raw["worktree"]),
        vcs=str(raw["vcs"]) if raw.get("vcs") is not None else None,
        name=str(raw["name"]) if raw.get("name") is not None else None,
        icon_url=str(raw["icon_url"]) if raw.get("icon_url") is not None else None,
        icon_color=str(raw["icon_color"])
        if raw.get("icon_color") is not None
        else None,
        sandboxes=sandboxes if isinstance(sandboxes, list) else [],
        commands=commands,
        row=raw,
    )


def _parse_workspace(row: sqlite3.Row, *, path: Path) -> RawWorkspace:
    raw = _row_to_dict(row)
    extra = _optional_json(raw.get("extra"), label="workspace.extra", path=path)
    return RawWorkspace(
        id=str(raw["id"]),
        branch=str(raw["branch"]) if raw.get("branch") is not None else None,
        project_id=str(raw["project_id"]),
        type=str(raw["type"]),
        name=str(raw["name"]) if raw.get("name") is not None else None,
        directory=str(raw["directory"]) if raw.get("directory") is not None else None,
        extra=extra,
        row=raw,
    )


def _parse_message(row: sqlite3.Row, *, path: Path) -> RawMessage:
    raw = _row_to_dict(row)
    return RawMessage(
        id=str(raw["id"]),
        session_id=str(raw["session_id"]),
        time_created=_from_millis(raw.get("time_created")),
        time_updated=_from_millis(raw.get("time_updated")),
        data=_loads_json(str(raw["data"]), label=f"message:{raw['id']}", path=path),
        row=raw,
    )


def _parse_part(row: sqlite3.Row, *, path: Path) -> RawPart:
    raw = _row_to_dict(row)
    return RawPart(
        id=str(raw["id"]),
        message_id=str(raw["message_id"]),
        session_id=str(raw["session_id"]),
        time_created=_from_millis(raw.get("time_created")),
        time_updated=_from_millis(raw.get("time_updated")),
        data=_loads_json(str(raw["data"]), label=f"part:{raw['id']}", path=path),
        row=raw,
    )


def _parse_todo(row: sqlite3.Row) -> RawTodo:
    raw = _row_to_dict(row)
    return RawTodo(
        session_id=str(raw["session_id"]),
        content=str(raw["content"]),
        status=str(raw["status"]),
        priority=str(raw["priority"]),
        position=int(raw["position"]),
        time_created=_from_millis(raw.get("time_created")),
        time_updated=_from_millis(raw.get("time_updated")),
        row=raw,
    )


def parse_session_source(
    connection: sqlite3.Connection, *, path: Path, session_id: str | None = None
) -> ParsedSessionSource:
    try:
        session_row = (
            connection.execute(
                "select * from session where id = ?",
                (session_id,),
            ).fetchone()
            if session_id is not None
            else connection.execute(
                "select * from session order by time_updated desc limit 1"
            ).fetchone()
        )
    except sqlite3.Error as exc:
        raise classify_sqlite_error(path, exc) from exc

    if session_row is None:
        if session_id is None:
            raise OpenCodePartialSourceError(
                path, "OpenCode source does not contain any sessions"
            )
        raise OpenCodePartialSourceError(
            path, f"OpenCode session not found: {session_id}"
        )

    session = _parse_session(session_row, path=path)

    try:
        project_row = connection.execute(
            "select * from project where id = ?",
            (session.project_id,),
        ).fetchone()
        workspace_row = None
        if session.workspace_id is not None:
            workspace_row = connection.execute(
                "select * from workspace where id = ?",
                (session.workspace_id,),
            ).fetchone()
        message_rows = connection.execute(
            "select * from message where session_id = ? order by time_created, id",
            (session.id,),
        ).fetchall()
        part_rows = connection.execute(
            "select * from part where session_id = ? order by time_created, id",
            (session.id,),
        ).fetchall()
        todo_rows = connection.execute(
            "select * from todo where session_id = ? order by position, time_created",
            (session.id,),
        ).fetchall()
    except sqlite3.Error as exc:
        raise classify_sqlite_error(path, exc) from exc

    messages = tuple(_parse_message(row, path=path) for row in message_rows)
    parsed_parts = tuple(_parse_part(row, path=path) for row in part_rows)
    parts_by_message: dict[str, list[RawPart]] = {}
    for part in parsed_parts:
        parts_by_message.setdefault(part.message_id, []).append(part)

    return ParsedSessionSource(
        path=path,
        session=session,
        project=_parse_project(project_row, path=path)
        if project_row is not None
        else None,
        workspace=_parse_workspace(workspace_row, path=path)
        if workspace_row is not None
        else None,
        messages=messages,
        parts_by_message={key: tuple(value) for key, value in parts_by_message.items()},
        todos=tuple(_parse_todo(row) for row in todo_rows),
    )


__all__ = [
    "ParsedSessionSource",
    "RawMessage",
    "RawPart",
    "RawProject",
    "RawSession",
    "RawTodo",
    "RawWorkspace",
    "parse_session_source",
]
