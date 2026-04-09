from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .zones import StoragePaths

type RawRef = Mapping[str, object]
type NormalizedRecord = dict[str, object]


class ProvenanceTracker:
    """Attach and retrieve raw-source provenance for normalized records."""

    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    def attach_raw_refs(
        self, record: NormalizedRecord, raw_ref: RawRef | Sequence[RawRef]
    ) -> NormalizedRecord:
        """Attach normalized raw-source references to a record."""
        refs = self._normalize_raw_refs(raw_ref)
        linked = copy.deepcopy(record)
        linked["raw_ref"] = refs[0]
        linked["provenance"] = {
            "raw_refs": refs,
            "link_chain": ["normalized", "raw"],
        }
        return linked

    def query_raw_sources(
        self, record_or_path: NormalizedRecord | str | Path
    ) -> list[RawRef]:
        """Return unique raw-source references for a record or record path."""
        if isinstance(record_or_path, (str, Path)):
            candidate = Path(record_or_path)
            if not candidate.is_absolute():
                candidate = self.paths.root / candidate
            record = json.loads(candidate.read_text(encoding="utf-8"))
        else:
            record = record_or_path

        refs: list[RawRef] = []
        raw_ref_value = record.get("raw_ref")
        if isinstance(raw_ref_value, dict):
            refs.append({str(key): value for key, value in raw_ref_value.items()})

        provenance = record.get("provenance")
        if isinstance(provenance, dict):
            provenance_map = {str(key): value for key, value in provenance.items()}
            raw_refs = provenance_map.get("raw_refs")
            for raw_ref in raw_refs if isinstance(raw_refs, list) else []:
                if isinstance(raw_ref, dict):
                    refs.append({str(key): value for key, value in raw_ref.items()})

        unique_refs: list[RawRef] = []
        seen: set[tuple[str, str]] = set()
        for raw_ref in refs:
            key = (str(raw_ref.get("sha256", "")), str(raw_ref.get("path", "")))
            if key in seen:
                continue
            seen.add(key)
            unique_refs.append(raw_ref)
        return unique_refs

    @staticmethod
    def _normalize_raw_refs(
        raw_ref: RawRef | Sequence[RawRef],
    ) -> list[dict[str, object]]:
        refs = (
            list(raw_ref)
            if isinstance(raw_ref, Sequence) and not isinstance(raw_ref, Mapping)
            else [raw_ref]
        )
        normalized: list[dict[str, object]] = []
        for ref in refs:
            if not isinstance(ref, Mapping):
                raise TypeError("raw_ref must be a mapping or list of mappings")
            if not {"sha256", "path", "size", "mtime"}.issubset(ref):
                raise ValueError("raw_ref must include sha256, path, size, and mtime")
            normalized.append({str(key): value for key, value in ref.items()})
        if not normalized:
            raise ValueError("at least one raw_ref is required for provenance")
        return normalized
