from __future__ import annotations

import os
from pathlib import Path

from snowiki.storage.zones import StoragePaths

DEFAULT_SNOWIKI_ROOT = Path("~/.snowiki")
SNOWIKI_ROOT_ENV_VAR = "SNOWIKI_ROOT"
_REPO_ROOT = Path(__file__).resolve().parent.parent


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


def get_repo_root() -> Path:
    return _REPO_ROOT


def resolve_repo_asset_path(relative_path: str | Path) -> Path:
    return get_repo_root() / Path(relative_path)
