from __future__ import annotations

from pathlib import Path

DEFAULT_EXCLUDED_PATH_SUFFIXES = (
    ".local/share/opencode/auth.json",
    ".env",
    ".env.local",
    "credentials.json",
)


def _normalized_candidate(path: str | Path) -> Path:
    return Path(path).expanduser()


def explain_exclusion(path: str | Path) -> str | None:
    candidate = _normalized_candidate(path)
    normalized = candidate.as_posix()
    basename = candidate.name
    for suffix in DEFAULT_EXCLUDED_PATH_SUFFIXES:
        if normalized.endswith(suffix) or basename == suffix:
            return f"sensitive path excluded from ingest: {suffix}"
    return None


def is_excluded_path(path: str | Path) -> bool:
    return explain_exclusion(path) is not None
