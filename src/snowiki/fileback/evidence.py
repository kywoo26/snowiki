from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from snowiki.storage.provenance import (
    dedupe_raw_refs as dedupe_provenance_raw_refs,
)
from snowiki.storage.provenance import raw_refs_from_record
from snowiki.storage.zones import isoformat_utc, relative_to_root

from .models import (
    EvidenceResolution,
    LoadedNormalizedRecord,
    RawRefDict,
    coerce_raw_ref,
    is_raw_ref_mapping,
)


def resolve_evidence(root: Path, requested_paths: Sequence[str]) -> EvidenceResolution:
    """Resolve supporting evidence paths into normalized and raw provenance."""
    normalized_records = _load_normalized_records(root)
    normalized_by_id = {record["id"]: record for record in normalized_records}
    resolved_compiled: list[str] = []
    resolved_normalized: list[str] = []
    resolved_raw: list[str] = []
    supporting_record_ids: list[str] = []
    supporting_raw_refs: list[RawRefDict] = []

    for requested in requested_paths:
        candidate = _resolve_workspace_path(root, requested)
        relative_path = relative_to_root(root, candidate)
        top_level = (
            candidate.parts[len(root.parts)]
            if len(candidate.parts) > len(root.parts)
            else ""
        )
        if top_level == "compiled":
            resolved_compiled.append(relative_path)
            record_ids = _compiled_record_ids(candidate)
            for record_id in record_ids:
                record = normalized_by_id.get(record_id)
                if record is None:
                    continue
                supporting_record_ids.append(record_id)
                resolved_normalized.append(record["path"])
                supporting_raw_refs.extend(record["raw_refs"])
            continue
        if top_level == "normalized":
            record = _normalized_record_for_path(normalized_records, relative_path)
            resolved_normalized.append(relative_path)
            supporting_record_ids.append(record["id"])
            supporting_raw_refs.extend(record["raw_refs"])
            continue
        if top_level == "raw":
            resolved_raw.append(relative_path)
            supporting_raw_refs.append(build_workspace_raw_ref(root, candidate))
            continue
        raise ValueError(
            f"unsupported evidence path '{requested}'; expected a raw/, normalized/, or compiled/ workspace path"
        )

    return {
        "requested_paths": list(requested_paths),
        "resolved_paths": {
            "compiled": sorted(set(resolved_compiled)),
            "normalized": sorted(set(resolved_normalized)),
            "raw": sorted(set(resolved_raw)),
        },
        "supporting_record_ids": sorted(set(supporting_record_ids)),
        "supporting_raw_refs": dedupe_raw_refs(supporting_raw_refs),
    }


def build_workspace_raw_ref(root: Path, path: Path) -> RawRefDict:
    """Build a raw-ref-style payload for an existing workspace artifact."""
    stat = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "path": relative_to_root(root, path),
        "size": stat.st_size,
        "mtime": isoformat_utc(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
    }


def dedupe_raw_refs(raw_refs: Sequence[Mapping[str, object]]) -> list[RawRefDict]:
    """Deduplicate raw refs using the compiler provenance key."""
    return [
        coerce_raw_ref(raw_ref)
        for raw_ref in dedupe_provenance_raw_refs(raw_refs, sort=True)
    ]


def dedupe_supporting_raw_refs(
    raw_refs: Sequence[Mapping[str, object]], manual_raw_path: str
) -> list[RawRefDict]:
    return [
        raw_ref
        for raw_ref in dedupe_raw_refs(raw_refs)
        if raw_ref["path"] != "" and raw_ref["path"] != manual_raw_path
    ]


def normalize_requested_paths(evidence_paths: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for path in evidence_paths:
        stripped = str(path).strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _compiled_record_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return []
    record_ids: list[str] = []
    in_record_ids = False
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("record_ids:"):
            in_record_ids = True
            continue
        if not in_record_ids:
            continue
        if line.startswith("  - "):
            item = line[4:].strip()
            if item:
                record_ids.append(_parse_list_scalar(item))
            continue
        if line and not line[0].isspace():
            in_record_ids = False
    return sorted(set(record_ids))


def _load_normalized_records(root: Path) -> list[LoadedNormalizedRecord]:
    records: list[LoadedNormalizedRecord] = []
    normalized_root = root / "normalized"
    if not normalized_root.exists():
        return records
    for path in sorted(
        normalized_root.rglob("*.json"), key=lambda item: item.as_posix()
    ):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        payload = {str(key): value for key, value in loaded.items()}
        records.append(
            {
                "id": str(payload.get("id", path.stem)),
                "path": relative_to_root(root, path),
                "raw_refs": _query_raw_sources(payload),
            }
        )
    return records


def _normalized_record_for_path(
    normalized_records: Sequence[LoadedNormalizedRecord], relative_path: str
) -> LoadedNormalizedRecord:
    for record in normalized_records:
        if record["path"] == relative_path:
            return record
    raise ValueError(f"normalized evidence path '{relative_path}' was not found")


def _parse_list_scalar(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith(('"', "'")):
        try:
            return str(json.loads(stripped))
        except json.JSONDecodeError:
            return stripped.strip("\"'")
    return stripped


def _query_raw_sources(record: Mapping[str, object]) -> list[RawRefDict]:
    refs: list[RawRefDict] = []
    for raw_ref_mapping in raw_refs_from_record(record):
        if is_raw_ref_mapping(raw_ref_mapping):
            refs.append(coerce_raw_ref(raw_ref_mapping))
    return dedupe_raw_refs(refs)


def _resolve_workspace_path(root: Path, requested_path: str) -> Path:
    candidate = Path(requested_path).expanduser()
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    )
    try:
        _ = relative_to_root(root, resolved)
    except ValueError as exc:
        raise ValueError(
            f"evidence path '{requested_path}' must stay inside {root}"
        ) from exc
    if not resolved.exists():
        raise ValueError(f"evidence path '{requested_path}' does not exist")
    if not resolved.is_file():
        raise ValueError(f"evidence path '{requested_path}' must be a file")
    return resolved
