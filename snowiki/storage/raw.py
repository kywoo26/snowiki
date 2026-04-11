from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

from .zones import (
    StoragePaths,
    atomic_write_bytes,
    isoformat_utc,
    relative_to_root,
    sanitize_segment,
)


class RawStorage:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    @property
    def root(self) -> Path:
        return self.paths.root

    def path_for(self, source_type: str, sha256: str) -> Path:
        safe_source_type = sanitize_segment(source_type)
        return self.paths.raw / safe_source_type / sha256[:2] / sha256[2:]

    def store_bytes(
        self,
        source_type: str,
        content: bytes,
        *,
        source_name: str | None = None,
        mtime: datetime | float | int | None = None,
    ) -> dict[str, object]:
        del source_name

        digest = hashlib.sha256(content).hexdigest()
        target = self.path_for(source_type, digest)

        if not target.exists():
            atomic_write_bytes(target, content)
            if mtime is not None:
                timestamp = self._mtime_to_timestamp(mtime)
                os.utime(target, (timestamp, timestamp))

        stat = target.stat()
        return {
            "sha256": digest,
            "path": relative_to_root(self.root, target),
            "size": stat.st_size,
            "mtime": isoformat_utc(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
        }

    def store_file(self, source_type: str, file_path: str | Path) -> dict[str, object]:
        source_path = Path(file_path)
        stat = source_path.stat()
        return self.store_bytes(
            source_type,
            source_path.read_bytes(),
            source_name=source_path.name,
            mtime=stat.st_mtime,
        )

    @staticmethod
    def _mtime_to_timestamp(value: datetime | float | int) -> float:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC).timestamp()
        return float(value)
