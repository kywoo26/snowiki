from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .zones import StoragePaths, atomic_write_json, read_json


class DedupeEngine:
    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()
        self.registry_dir = self.paths.index / "dedupe"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.raw_registry_path = self.registry_dir / "raw.json"
        self.identity_registry_path = self.registry_dir / "identities.json"

    def raw_fingerprint(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def stable_id(self, record_type: str, *parts: object) -> str:
        payload = json.dumps(
            parts,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{record_type}_{digest[:32]}"

    def build_identity_key(
        self,
        *,
        record_type: str,
        source_type: str,
        payload: dict[str, Any],
        identity_key: str | None = None,
    ) -> str:
        if identity_key is not None:
            return identity_key
        canonical = {
            "payload": payload,
            "record_type": record_type,
            "source_type": source_type,
        }
        rendered = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def register_raw(self, raw_ref: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        registry = read_json(self.raw_registry_path, {})
        sha256 = str(raw_ref["sha256"])
        if sha256 in registry:
            return registry[sha256], True
        registry[sha256] = dict(raw_ref)
        atomic_write_json(self.raw_registry_path, registry)
        return dict(raw_ref), False

    def lookup_raw(self, sha256: str) -> dict[str, Any] | None:
        registry = read_json(self.raw_registry_path, {})
        entry = registry.get(sha256)
        return dict(entry) if isinstance(entry, dict) else None

    def register_identity(
        self,
        *,
        record_type: str,
        identity_key: str,
        record_id: str,
        path: str,
    ) -> tuple[dict[str, Any], bool]:
        registry = read_json(self.identity_registry_path, {})
        bucket = registry.setdefault(record_type, {})
        if identity_key in bucket:
            return dict(bucket[identity_key]), True
        entry = {
            "identity_key": identity_key,
            "path": path,
            "record_id": record_id,
            "record_type": record_type,
        }
        bucket[identity_key] = entry
        atomic_write_json(self.identity_registry_path, registry)
        return dict(entry), False

    def lookup_identity(
        self, record_type: str, identity_key: str
    ) -> dict[str, Any] | None:
        registry = read_json(self.identity_registry_path, {})
        entry = registry.get(record_type, {}).get(identity_key)
        return dict(entry) if isinstance(entry, dict) else None
