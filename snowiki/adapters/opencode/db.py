from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

from .failures import (
    OpenCodePartialSourceError,
    classify_sqlite_error,
)

DEFAULT_OPENCODE_DB_PATH = Path("~/.local/share/opencode/opencode.db").expanduser()
REQUIRED_TABLES = {"message", "part", "project", "session", "todo", "workspace"}


def _database_uri(path: Path) -> str:
    return f"file:{quote(str(path))}?mode=ro"


def checksum_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def connect_sqlite(path: Path | None = None) -> sqlite3.Connection:
    db_path = (path or DEFAULT_OPENCODE_DB_PATH).expanduser().resolve()
    try:
        connection = sqlite3.connect(_database_uri(db_path), uri=True)
    except sqlite3.Error as exc:
        raise classify_sqlite_error(db_path, exc) from exc
    connection.row_factory = sqlite3.Row
    return connection


def ensure_required_tables(connection: sqlite3.Connection, path: Path) -> None:
    try:
        with closing(connection.cursor()) as cursor:
            rows = cursor.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
    except sqlite3.Error as exc:
        raise classify_sqlite_error(path, exc) from exc

    table_names = {str(row[0]) for row in rows}
    missing_tables = sorted(REQUIRED_TABLES - table_names)
    if missing_tables:
        joined = ", ".join(missing_tables)
        raise OpenCodePartialSourceError(
            path, f"missing required SQLite tables: {joined}"
        )


def safe_connect_sqlite(path: Path | None = None) -> tuple[Path, sqlite3.Connection]:
    db_path = (path or DEFAULT_OPENCODE_DB_PATH).expanduser().resolve()
    if not db_path.exists():
        raise OpenCodePartialSourceError(
            db_path, "OpenCode database path does not exist"
        )
    connection = connect_sqlite(db_path)
    ensure_required_tables(connection, db_path)
    return db_path, connection


__all__ = [
    "DEFAULT_OPENCODE_DB_PATH",
    "REQUIRED_TABLES",
    "checksum_sha256",
    "connect_sqlite",
    "ensure_required_tables",
    "safe_connect_sqlite",
]
