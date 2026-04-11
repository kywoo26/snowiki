from __future__ import annotations

from contextlib import closing
from pathlib import Path

from .db import DEFAULT_OPENCODE_DB_PATH, safe_connect_sqlite
from .failures import (
    OpenCodeLockedSourceError,
    OpenCodePartialSourceError,
)
from .normalizer import (
    NormalizedOpenCodeSession,
    build_failure_result,
    normalize_session_source,
)
from .parser import parse_session_source


def load_opencode_session(
    session_id: str | None = None,
    *,
    db_path: Path | None = None,
) -> NormalizedOpenCodeSession:
    resolved_path = (db_path or DEFAULT_OPENCODE_DB_PATH).expanduser().resolve()
    try:
        actual_path, connection = safe_connect_sqlite(resolved_path)
        with closing(connection):
            parsed = parse_session_source(
                connection, path=actual_path, session_id=session_id
            )
        return normalize_session_source(parsed)
    except (OpenCodeLockedSourceError, OpenCodePartialSourceError) as exc:
        return build_failure_result(
            db_path=resolved_path, session_id=session_id, error=exc
        )


__all__ = [
    "DEFAULT_OPENCODE_DB_PATH",
    "NormalizedOpenCodeSession",
    "OpenCodeLockedSourceError",
    "OpenCodePartialSourceError",
    "load_opencode_session",
]
