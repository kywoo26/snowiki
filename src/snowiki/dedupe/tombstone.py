from __future__ import annotations

from pathlib import Path

from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_json,
    isoformat_utc,
    read_json,
)


class TombstoneStore:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()
        self.tombstone_path = self.paths.index / "dedupe" / "tombstones.json"
        self.tombstone_path.parent.mkdir(parents=True, exist_ok=True)

    def mark_deleted(
        self,
        *,
        record_type: str,
        identity_key: str,
        record_id: str,
        path: str,
        deleted_at: str,
    ) -> dict[str, str]:
        registry = read_json(self.tombstone_path, {})
        bucket = registry.setdefault(record_type, {})
        entry = {
            "deleted_at": isoformat_utc(deleted_at),
            "identity_key": identity_key,
            "path": path,
            "record_id": record_id,
            "record_type": record_type,
            "status": "deleted",
        }
        bucket[identity_key] = entry
        atomic_write_json(self.tombstone_path, registry)
        return entry

    def lookup(self, record_type: str, identity_key: str) -> dict[str, str] | None:
        registry = read_json(self.tombstone_path, {})
        entry = registry.get(record_type, {}).get(identity_key)
        return dict(entry) if isinstance(entry, dict) else None

    def is_tombstoned(self, record_type: str, identity_key: str) -> bool:
        return self.lookup(record_type, identity_key) is not None
