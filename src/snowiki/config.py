from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from snowiki.storage.zones import StoragePaths

DEFAULT_SNOWIKI_ROOT = Path("~/.snowiki")
SNOWIKI_ROOT_ENV_VAR = "SNOWIKI_ROOT"
DEFAULT_RUNTIME_LEXICAL_POLICY = "legacy-lexical"
RUNTIME_LEXICAL_POLICY_ENV_VAR = "SNOWIKI_LEXICAL_POLICY"
SUPPORTED_RUNTIME_LEXICAL_POLICIES = (
    DEFAULT_RUNTIME_LEXICAL_POLICY,
    "korean-mixed-lexical",
)
RuntimeLexicalPolicySource = Literal["cli", "env", "config", "default"]


@dataclass(frozen=True, slots=True)
class RuntimeLexicalPolicySelection:
    """Normalized runtime lexical policy selection result."""

    policy: str
    source: RuntimeLexicalPolicySource


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


def normalize_runtime_lexical_policy(policy: str) -> str:
    """Normalize and validate a runtime lexical policy identifier."""

    normalized_policy = policy.strip().casefold()
    if normalized_policy not in SUPPORTED_RUNTIME_LEXICAL_POLICIES:
        supported = ", ".join(SUPPORTED_RUNTIME_LEXICAL_POLICIES)
        raise ValueError(
            f"unsupported runtime lexical policy '{policy}'; expected one of: {supported}"
        )
    return normalized_policy


def select_runtime_lexical_policy(
    cli_policy: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    config_policy: str | None = None,
) -> RuntimeLexicalPolicySelection:
    """Resolve runtime lexical policy with CLI > env > config > default precedence."""

    if cli_policy is not None:
        return RuntimeLexicalPolicySelection(
            policy=normalize_runtime_lexical_policy(cli_policy),
            source="cli",
        )

    env_policy = (env or os.environ).get(RUNTIME_LEXICAL_POLICY_ENV_VAR)
    if env_policy:
        return RuntimeLexicalPolicySelection(
            policy=normalize_runtime_lexical_policy(env_policy),
            source="env",
        )

    if config_policy is not None:
        return RuntimeLexicalPolicySelection(
            policy=normalize_runtime_lexical_policy(config_policy),
            source="config",
        )

    return RuntimeLexicalPolicySelection(
        policy=DEFAULT_RUNTIME_LEXICAL_POLICY,
        source="default",
    )


def resolve_runtime_lexical_policy(
    cli_policy: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    config_policy: str | None = None,
) -> str:
    """Return the effective runtime lexical policy identifier."""

    return select_runtime_lexical_policy(
        cli_policy,
        env=env,
        config_policy=config_policy,
    ).policy


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    return _discover_repo_root(Path(__file__).resolve().parent)


def resolve_repo_asset_path(relative_path: str | Path) -> Path:
    return get_repo_root() / Path(relative_path)
