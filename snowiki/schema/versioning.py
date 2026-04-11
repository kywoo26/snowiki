from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any


class SchemaVersion(StrEnum):
    V1_LEGACY = "1.0.0"
    V2_CANONICAL = "2.0.0"


CURRENT_SCHEMA_VERSION = SchemaVersion.V2_CANONICAL
MigrationHook = Callable[[dict[str, Any]], dict[str, Any]]

_MIGRATIONS: dict[tuple[SchemaVersion, SchemaVersion], MigrationHook] = {}


def register_migration(
    from_version: SchemaVersion,
    to_version: SchemaVersion,
    hook: MigrationHook,
) -> None:
    _MIGRATIONS[(from_version, to_version)] = hook


def migrate_payload(
    payload: Mapping[str, Any],
    from_version: SchemaVersion,
    to_version: SchemaVersion = CURRENT_SCHEMA_VERSION,
) -> dict[str, Any]:
    working_copy = dict(payload)
    if from_version == to_version:
        return working_copy

    hook = _MIGRATIONS.get((from_version, to_version))
    if hook is None:
        raise ValueError(
            f"No migration hook registered for {from_version.value} -> {to_version.value}",
        )

    migrated = hook(working_copy)
    migrated.setdefault("schema_version", to_version)
    return migrated
