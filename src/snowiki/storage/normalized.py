from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TypedDict, cast

from snowiki.privacy import PrivacyGate

from .dedupe import DedupeEngine
from .provenance import NormalizedRecord, ProvenanceTracker, RawRef
from .zones import (
    StoragePaths,
    atomic_write_json,
    ensure_utc_datetime,
    isoformat_utc,
    relative_to_root,
    sanitize_segment,
)

type TimestampInput = datetime | str | None


class StoreResult(TypedDict):
    """Serialized result returned after storing a normalized record."""

    id: str
    path: str
    record: NormalizedRecord


class MarkdownStoreResult(StoreResult):
    """Serialized result returned after storing a Markdown document."""

    status: str


class NormalizedStorage:
    """Persist normalized manifests, events, messages, and parts."""

    def __init__(
        self,
        root: str | Path,
        *,
        provenance: ProvenanceTracker | None = None,
    ) -> None:
        self.paths: StoragePaths = StoragePaths(Path(root))
        self.paths.ensure_all()
        self.provenance: ProvenanceTracker = provenance or ProvenanceTracker(self.paths.root)
        self.privacy: PrivacyGate = PrivacyGate()
        self._ids: DedupeEngine = DedupeEngine(self.paths.root)

    @property
    def root(self) -> Path:
        """Return the storage root directory."""
        return self.paths.root

    def path_for(
        self, *, source_type: str, record_id: str, recorded_at: TimestampInput
    ) -> Path:
        """Build the normalized storage path for a record."""
        moment = ensure_utc_datetime(recorded_at)
        safe_source_type = sanitize_segment(source_type)
        return (
            self.paths.normalized
            / safe_source_type
            / f"{moment.year:04d}"
            / f"{moment.month:02d}"
            / f"{moment.day:02d}"
            / f"{record_id}.json"
        )

    def path_for_markdown_document(self, record_id: str) -> Path:
        """Build the latest-only normalized path for a Markdown document."""
        return self.paths.normalized / "markdown" / "documents" / f"{record_id}.json"

    def store_manifest(
        self,
        *,
        source_type: str,
        record_id: str,
        manifest: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: TimestampInput,
    ) -> StoreResult:
        """Store a normalized manifest record."""
        return self.store_record(
            source_type=source_type,
            record_type="manifest",
            record_id=record_id,
            payload=manifest,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def store_event(
        self,
        *,
        source_type: str,
        record_id: str,
        event: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: TimestampInput,
    ) -> StoreResult:
        """Store a normalized event record."""
        return self.store_record(
            source_type=source_type,
            record_type="event",
            record_id=record_id,
            payload=event,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def store_message(
        self,
        *,
        source_type: str,
        record_id: str,
        message: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: TimestampInput,
    ) -> StoreResult:
        """Store a normalized message record."""
        return self.store_record(
            source_type=source_type,
            record_type="message",
            record_id=record_id,
            payload=message,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def store_part(
        self,
        *,
        source_type: str,
        record_id: str,
        part: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: TimestampInput,
    ) -> StoreResult:
        """Store a normalized part record."""
        return self.store_record(
            source_type=source_type,
            record_type="part",
            record_id=record_id,
            payload=part,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def store_record(
        self,
        *,
        source_type: str,
        record_type: str,
        record_id: str,
        payload: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: TimestampInput,
    ) -> StoreResult:
        """Store a normalized record with attached provenance."""
        if not record_id:
            raise ValueError("record_id is required")

        moment = ensure_utc_datetime(recorded_at)
        target = self.path_for(
            source_type=source_type, record_id=record_id, recorded_at=moment
        )
        record: NormalizedRecord = {
            **self.privacy.prepare_payload(dict(payload)),
            "id": record_id,
            "record_type": record_type,
            "recorded_at": isoformat_utc(moment),
            "source_type": source_type,
        }
        record = self.provenance.attach_raw_refs(record, raw_ref)

        _ = atomic_write_json(target, record)

        return {
            "id": record_id,
            "path": relative_to_root(self.root, target),
            "record": record,
        }

    def store_markdown_document(
        self,
        *,
        source_root: str,
        relative_path: str,
        payload: dict[str, object],
        raw_ref: RawRef,
        recorded_at: TimestampInput,
    ) -> MarkdownStoreResult:
        """Store a latest-only normalized Markdown document record."""
        if not source_root.strip():
            raise ValueError("source_root is required")
        if not relative_path.strip():
            raise ValueError("relative_path is required")

        record_id = self.deterministic_id("markdown_document", source_root, relative_path)
        target = self.path_for_markdown_document(record_id)
        moment = ensure_utc_datetime(recorded_at)
        existing_hash = self._existing_content_hash(target)
        content_hash = str(payload.get("content_hash", ""))
        status = "inserted" if existing_hash is None else "updated"
        if existing_hash == content_hash:
            status = "unchanged"

        record: NormalizedRecord = {
            **self.privacy.prepare_payload(dict(payload)),
            "id": record_id,
            "record_type": "document",
            "recorded_at": isoformat_utc(moment),
            "source_type": "markdown",
        }
        record = self.provenance.attach_raw_refs(record, raw_ref)

        if status != "unchanged":
            _ = atomic_write_json(target, record)

        return {
            "id": record_id,
            "path": relative_to_root(self.root, target),
            "record": record if status != "unchanged" else self.read_record(target),
            "status": status,
        }

    def deterministic_id(self, record_type: str, *parts: object) -> str:
        """Return a stable identifier for a normalized record."""
        return self._ids.stable_id(record_type, *parts)

    def _existing_content_hash(self, path: Path) -> str | None:
        if not path.exists():
            return None
        payload = self.read_record(path)
        value = payload.get("content_hash")
        return value if isinstance(value, str) else None

    def read_record(self, path: str | Path) -> NormalizedRecord:
        """Read a normalized record from disk."""
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        payload = cast(object, json.loads(candidate.read_text(encoding="utf-8")))
        if not isinstance(payload, dict):
            raise TypeError(f"normalized record at {candidate} must be a JSON object")
        payload_dict = cast(dict[object, object], payload)
        return {str(key): value for key, value in payload_dict.items()}
