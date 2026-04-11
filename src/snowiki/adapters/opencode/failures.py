from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OpenCodeSourceError(Exception):
    path: Path
    message: str

    def __str__(self) -> str:
        return self.message


class OpenCodeLockedSourceError(OpenCodeSourceError):
    pass


class OpenCodePartialSourceError(OpenCodeSourceError):
    pass


def classify_sqlite_error(path: Path, error: sqlite3.Error) -> OpenCodeSourceError:
    message = str(error).strip() or error.__class__.__name__
    lowered = message.lower()
    if "locked" in lowered or "busy" in lowered:
        return OpenCodeLockedSourceError(path, f"OpenCode source is locked: {message}")
    if (
        "malformed" in lowered
        or "not a database" in lowered
        or "unable to open database file" in lowered
        or "disk image is malformed" in lowered
        or "no such table" in lowered
    ):
        return OpenCodePartialSourceError(
            path, f"OpenCode source is partial or invalid: {message}"
        )
    return OpenCodePartialSourceError(
        path, f"OpenCode source could not be read safely: {message}"
    )


__all__ = [
    "OpenCodeLockedSourceError",
    "OpenCodePartialSourceError",
    "OpenCodeSourceError",
    "classify_sqlite_error",
]
