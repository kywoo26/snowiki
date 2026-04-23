from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from snowiki.storage.zones import StoragePaths

DEFAULT_SNOWIKI_ROOT = Path("~/.snowiki")
SNOWIKI_ROOT_ENV_VAR = "SNOWIKI_ROOT"


def _discover_repo_root(start: Path) -> Path:
    """Best-effort repository root discovery for repo-owned assets."""

    resolved_start = start.resolve()
    for candidate in (resolved_start, *resolved_start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return resolved_start


def _prepare_root(root: Path) -> Path:
    resolved_root = root.expanduser().resolve()
    StoragePaths(resolved_root).ensure_all()
    return resolved_root
def get_snowiki_root() -> Path:
    env_root = os.environ.get(SNOWIKI_ROOT_ENV_VAR)
    return _prepare_root(Path(env_root) if env_root else DEFAULT_SNOWIKI_ROOT)


def resolve_snowiki_root(root: Path | None) -> Path:
    if root is None:
        return get_snowiki_root()
    return _prepare_root(root)


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    return _discover_repo_root(Path(__file__).resolve().parent)


def resolve_repo_asset_path(relative_path: str | Path) -> Path:
    return get_repo_root() / Path(relative_path)
