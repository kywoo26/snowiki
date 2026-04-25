from __future__ import annotations

import copy
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from .zones import StoragePaths

type RawRef = Mapping[str, object]
type NormalizedRecord = dict[str, object]


def raw_refs_from_record(record: Mapping[str, object]) -> list[dict[str, object]]:
    """Return unique raw-source references from supported normalized record shapes."""
    refs: list[dict[str, object]] = []
    raw_ref = record.get("raw_ref")
    if isinstance(raw_ref, Mapping):
        refs.append(_string_key_mapping(cast(Mapping[object, object], raw_ref)))

    refs.extend(_raw_ref_sequence(record.get("raw_refs")))

    provenance = record.get("provenance")
    if isinstance(provenance, Mapping):
        provenance_map = _string_key_mapping(cast(Mapping[object, object], provenance))
        refs.extend(_raw_ref_sequence(provenance_map.get("raw_refs")))

    return _dedupe_raw_refs(refs)


def normalize_raw_refs(raw_ref: RawRef | Sequence[RawRef]) -> list[dict[str, object]]:
    """Normalize one or more raw-source references for storage."""
    refs: list[object] = [raw_ref] if isinstance(raw_ref, Mapping) else list(raw_ref)
    normalized: list[dict[str, object]] = []
    for ref in refs:
        if not isinstance(ref, Mapping):
            raise TypeError("raw_ref must be a mapping or list of mappings")
        ref_map = cast(Mapping[object, object], ref)
        if not all(key in ref_map for key in ("sha256", "path", "size", "mtime")):
            raise ValueError("raw_ref must include sha256, path, size, and mtime")
        normalized.append(_string_key_mapping(ref_map))
    if not normalized:
        raise ValueError("at least one raw_ref is required for provenance")
    return normalized


def dedupe_raw_refs(
    raw_refs: Iterable[Mapping[str, object]],
    *,
    sort: bool = False,
) -> list[dict[str, object]]:
    """Deduplicate raw-source references using Snowiki's provenance identity."""
    unique_refs: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for raw_ref in raw_refs:
        entry = _string_key_mapping(cast(Mapping[object, object], raw_ref))
        key = _raw_ref_identity(entry)
        if key in seen:
            continue
        seen.add(key)
        unique_refs.append(entry)
    if sort:
        unique_refs.sort(key=lambda entry: (_raw_ref_identity(entry)[1], _raw_ref_identity(entry)[0]))
    return unique_refs


def _raw_ref_sequence(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    refs = cast(list[object], value)
    return [
        _string_key_mapping(cast(Mapping[object, object], ref))
        for ref in refs
        if isinstance(ref, Mapping)
    ]


def _string_key_mapping(value: Mapping[object, object]) -> dict[str, object]:
    return {str(key): item for key, item in value.items()}


def _dedupe_raw_refs(refs: list[dict[str, object]]) -> list[dict[str, object]]:
    return dedupe_raw_refs(refs)


def _raw_ref_identity(raw_ref: Mapping[str, object]) -> tuple[str, str]:
    return (str(raw_ref.get("sha256", "")), str(raw_ref.get("path", "")))


class ProvenanceTracker:
    """Attach and retrieve raw-source provenance for normalized records."""

    paths: StoragePaths

    def __init__(self, root: str | Path) -> None:
        self.paths = StoragePaths(Path(root))
        self.paths.ensure_all()

    def attach_raw_refs(
        self, record: NormalizedRecord, raw_ref: RawRef | Sequence[RawRef]
    ) -> NormalizedRecord:
        """Attach normalized raw-source references to a record."""
        refs = normalize_raw_refs(raw_ref)
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
            loaded = cast(object, json.loads(candidate.read_text(encoding="utf-8")))
            if not isinstance(loaded, Mapping):
                return []
            record = _string_key_mapping(cast(Mapping[object, object], loaded))
        else:
            record = record_or_path
        return cast(list[RawRef], raw_refs_from_record(record))
