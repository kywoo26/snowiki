from __future__ import annotations

from pathlib import Path
from typing import Any

from .compiled import CompiledStorage
from .dedupe import DedupeEngine
from .index import IndexStorage
from .normalized import NormalizedStorage, TimestampInput
from .provenance import ProvenanceTracker
from .quarantine import QuarantineManager
from .raw import RawStorage
from .zones import StoragePaths, Zone


class StorageEngine:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

        self.provenance = ProvenanceTracker(self.paths.root)
        self.dedupe = DedupeEngine(self.paths.root)
        self.raw = RawStorage(self.paths.root)
        self.normalized = NormalizedStorage(self.paths.root, provenance=self.provenance)
        self.compiled = CompiledStorage(self.paths.root)
        self.index = IndexStorage(self.paths.root)
        self.quarantine = QuarantineManager(self.paths.root)

    @property
    def root(self) -> Path:
        return self.paths.root

    def ingest_record(
        self,
        *,
        source_type: str,
        source_name: str,
        content: bytes,
        record_type: str,
        payload: dict[str, Any],
        recorded_at: TimestampInput,
        identity_key: str | None = None,
        record_id: str | None = None,
    ) -> dict[str, Any]:
        raw_ref = self.raw.store_bytes(source_type, content, source_name=source_name)
        _, raw_duplicate = self.dedupe.register_raw(raw_ref)

        resolved_identity = self.dedupe.build_identity_key(
            record_type=record_type,
            source_type=source_type,
            payload=payload,
            identity_key=identity_key,
        )
        resolved_record_id = record_id or self.dedupe.stable_id(
            record_type, source_type, resolved_identity
        )

        existing = self.dedupe.lookup_identity(record_type, resolved_identity)
        if existing is not None:
            existing_path = self.root / str(existing["path"])
            if existing_path.exists():
                return {
                    **existing,
                    "duplicate": True,
                    "duplicate_raw": raw_duplicate,
                    "id": existing["record_id"],
                    "path": existing["path"],
                    "raw_ref": raw_ref,
                    "record": self.normalized.read_record(existing_path),
                }

        stored = self.normalized.store_record(
            source_type=source_type,
            record_type=record_type,
            record_id=resolved_record_id,
            payload=payload,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )
        self.dedupe.register_identity(
            record_type=record_type,
            identity_key=resolved_identity,
            record_id=resolved_record_id,
            path=str(stored["path"]),
        )
        return {
            **stored,
            "duplicate": False,
            "duplicate_raw": raw_duplicate,
            "identity_key": resolved_identity,
            "raw_ref": raw_ref,
        }


__all__ = [
    "CompiledStorage",
    "DedupeEngine",
    "IndexStorage",
    "NormalizedStorage",
    "ProvenanceTracker",
    "QuarantineManager",
    "RawStorage",
    "StorageEngine",
    "StoragePaths",
    "Zone",
]
