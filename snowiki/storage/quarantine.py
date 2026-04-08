from __future__ import annotations

from pathlib import Path

from .zones import (
    StoragePaths,
    atomic_write_bytes,
    atomic_write_json,
    isoformat_utc,
    relative_to_root,
    sanitize_segment,
)


class QuarantineManager:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    @property
    def root(self) -> Path:
        return self.paths.root

    def quarantine_bytes(
        self,
        *,
        source_name: str,
        content: bytes,
        reason: str,
        original_path: str | Path | None = None,
        timestamp: str | None = None,
    ) -> dict[str, str]:
        timestamp_value = isoformat_utc(timestamp).replace(":", "").replace("-", "")
        bucket_name = f"{timestamp_value}_{sanitize_segment(Path(source_name).name)}"
        bucket_path = self.paths.quarantine / bucket_name
        bucket_path.mkdir(parents=True, exist_ok=True)

        payload_name = Path(source_name).name or "payload.bin"
        payload_path = bucket_path / payload_name
        metadata_path = bucket_path / "metadata.json"

        atomic_write_bytes(payload_path, content)
        atomic_write_json(
            metadata_path,
            {
                "original_path": str(original_path)
                if original_path is not None
                else None,
                "reason": reason,
                "source_name": source_name,
                "timestamp": isoformat_utc(timestamp),
            },
        )

        return {
            "bucket_path": relative_to_root(self.root, bucket_path),
            "metadata_path": relative_to_root(self.root, metadata_path),
            "payload_path": relative_to_root(self.root, payload_path),
        }

    def quarantine_file(
        self,
        *,
        file_path: str | Path,
        reason: str,
        timestamp: str | None = None,
    ) -> dict[str, str]:
        candidate = Path(file_path)
        return self.quarantine_bytes(
            source_name=candidate.name,
            content=candidate.read_bytes(),
            reason=reason,
            original_path=candidate,
            timestamp=timestamp,
        )
