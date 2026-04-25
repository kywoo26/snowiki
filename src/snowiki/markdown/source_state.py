from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from posixpath import normpath
from typing import Any, Literal, NotRequired, TypedDict

from snowiki.markdown.discovery import MARKDOWN_SUFFIXES, discover_markdown_sources
from snowiki.privacy import PrivacyGate
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.storage.provenance import raw_refs_from_record
from snowiki.storage.zones import atomic_write_json, isoformat_utc, relative_to_root

MarkdownSourceState = Literal["invalid", "current", "modified", "missing", "untracked"]


class MarkdownSourceStateItem(TypedDict):
    state: MarkdownSourceState
    source_root: str
    relative_path: str
    source_path: str
    stored_content_hash: str | None
    current_content_hash: str | None
    normalized_path: NotRequired[str]
    record_id: NotRequired[str]
    raw_paths: NotRequired[list[str]]
    error: NotRequired[str]


class MarkdownSourceStateReport(TypedDict):
    total: int
    counts: dict[str, int]
    stale_count: int
    items: list[MarkdownSourceStateItem]


class SourcePruneCandidate(TypedDict):
    kind: str
    path: str
    reason: str
    record_id: str | None
    source_path: str | None


class SourcePruneResult(TypedDict):
    root: str
    dry_run: bool
    candidate_count: int
    deleted_count: int
    candidates: list[SourcePruneCandidate]
    deleted: list[str]
    tombstone_path: str | None
    rebuild: dict[str, object] | None


class _MarkdownRecord(TypedDict):
    id: str
    path: str
    source_root: str
    relative_path: str
    source_path: str
    content_hash: str
    raw_paths: list[str]
    error: NotRequired[str]


def collect_markdown_source_state(root: str | Path) -> MarkdownSourceStateReport:
    """Classify live Markdown files against normalized Markdown records."""
    base = Path(root)
    records = _load_markdown_records(base)
    items = [_classify_record(record) for record in records]
    items.extend(_untracked_items(records))
    items.sort(key=_item_sort_key)
    counts: Counter[str] = Counter(item["state"] for item in items)
    normalized_counts: dict[str, int] = {state: counts[state] for state in _state_order()}
    return {
        "total": len(items),
        "counts": normalized_counts,
        "stale_count": sum(normalized_counts[state] for state in _stale_states()),
        "items": items,
    }


def count_stale_markdown_sources(
    root: str | Path,
    *,
    source_root: str | Path | None = None,
    include_untracked: bool = True,
) -> int:
    """Count stale Markdown records, optionally including untracked files."""
    expected_root = _normalize_source_root(Path(source_root)) if source_root else None
    states = set(_stale_states())
    if not include_untracked:
        states.discard("untracked")
    return sum(
        1
        for item in collect_markdown_source_state(root)["items"]
        if item["state"] in states
        and (expected_root is None or item["source_root"] == expected_root)
    )


def prune_missing_markdown_sources(
    root: str | Path, *, dry_run: bool = True
) -> SourcePruneResult:
    """Prune normalized Markdown records whose source files are missing."""
    resolved_root = Path(root).expanduser().resolve()
    candidates = plan_missing_source_prune(resolved_root)
    if dry_run:
        return _prune_result(
            root=resolved_root,
            dry_run=True,
            candidates=candidates,
            deleted=[],
            tombstone_path=None,
            rebuild=None,
        )
    deleted = _delete_candidates(resolved_root, candidates)
    tombstone_path = _write_tombstone(resolved_root, candidates, deleted)
    rebuild = run_rebuild_with_integrity(resolved_root) if deleted else None
    return _prune_result(
        root=resolved_root,
        dry_run=False,
        candidates=candidates,
        deleted=deleted,
        tombstone_path=tombstone_path,
        rebuild=rebuild,
    )


def plan_missing_source_prune(root: str | Path) -> list[SourcePruneCandidate]:
    """Return deletion candidates for missing-source Markdown records."""
    resolved_root = Path(root).expanduser().resolve()
    report = collect_markdown_source_state(resolved_root)
    missing_items = [item for item in report["items"] if item["state"] == "missing"]
    raw_reference_counts = _raw_reference_counts(resolved_root)
    candidates: list[SourcePruneCandidate] = []
    for item in missing_items:
        normalized_path = item.get("normalized_path")
        if normalized_path is None:
            continue
        candidates.append(
            {
                "kind": "normalized_markdown_record",
                "path": normalized_path,
                "reason": "source_missing",
                "record_id": item.get("record_id"),
                "source_path": item["source_path"],
            }
        )
        for raw_path in item.get("raw_paths", []):
            target = _zone_file_path(resolved_root, raw_path, zone="raw")
            if target is None or raw_reference_counts.get(raw_path) != 1:
                continue
            candidates.append(
                {
                    "kind": "raw_snapshot",
                    "path": raw_path,
                    "reason": "unreferenced_after_source_prune",
                    "record_id": item.get("record_id"),
                    "source_path": item["source_path"],
                }
            )
    return sorted(candidates, key=lambda candidate: (candidate["kind"], candidate["path"]))


def _load_markdown_records(root: Path) -> list[_MarkdownRecord]:
    records: list[_MarkdownRecord] = []
    documents_root = root / "normalized" / "markdown" / "documents"
    for path in sorted(documents_root.glob("*.json"), key=lambda item: item.as_posix()):
        try:
            payload = _load_json_object(path)
        except json.JSONDecodeError:
            continue
        record = _record_from_payload(path=path, root=root, payload=payload)
        if record is not None:
            records.append(record)
    return records


def _record_from_payload(
    *, path: Path, root: Path, payload: dict[str, object]
) -> _MarkdownRecord | None:
    if payload.get("source_type") != "markdown" or payload.get("record_type") != "document":
        return None
    record_id = _string_value(payload.get("id"))
    if record_id is None:
        return None
    source_root = _string_value(payload.get("source_root"))
    if source_root is None:
        return None
    relative_path = _string_value(payload.get("relative_path"))
    if relative_path is None:
        return None
    stored_source_path = _string_value(payload.get("source_path"))
    content_hash = _string_value(payload.get("content_hash"))
    if content_hash is None:
        return None
    source_path = _source_path_from_identity(source_root, relative_path)
    error = _source_metadata_error(
        source_root=source_root,
        relative_path=relative_path,
        stored_source_path=stored_source_path,
    )
    record: _MarkdownRecord = {
        "id": record_id,
        "path": path.relative_to(root).as_posix(),
        "source_root": source_root,
        "relative_path": relative_path,
        "source_path": source_path,
        "content_hash": content_hash,
        "raw_paths": _raw_paths(payload),
    }
    if error is not None:
        record["error"] = error
    return record


def _classify_record(record: _MarkdownRecord) -> MarkdownSourceStateItem:
    if "error" in record:
        return _record_item(record, state="invalid", current_content_hash=None)
    source_path = Path(record["source_path"])
    if not source_path.exists():
        return _record_item(record, state="missing", current_content_hash=None)
    if source_path.is_symlink() or not source_path.is_file():
        return _record_item(
            _record_with_error(record, "source path is not a regular file"),
            state="invalid",
            current_content_hash=None,
        )
    try:
        PrivacyGate().ensure_allowed_source(source_path)
    except ValueError as exc:
        return _record_item(
            _record_with_error(record, str(exc)),
            state="invalid",
            current_content_hash=None,
        )
    current_hash = _sha256_file(source_path)
    state: MarkdownSourceState = "current" if current_hash == record["content_hash"] else "modified"
    return _record_item(record, state=state, current_content_hash=current_hash)


def _record_item(
    record: _MarkdownRecord,
    *,
    state: MarkdownSourceState,
    current_content_hash: str | None,
) -> MarkdownSourceStateItem:
    item: MarkdownSourceStateItem = {
        "state": state,
        "record_id": record["id"],
        "source_root": record["source_root"],
        "relative_path": record["relative_path"],
        "source_path": record["source_path"],
        "normalized_path": record["path"],
        "stored_content_hash": record["content_hash"],
        "current_content_hash": current_content_hash,
        "raw_paths": record["raw_paths"],
    }
    if "error" in record:
        item["error"] = record["error"]
    return item


def _record_with_error(record: _MarkdownRecord, error: str) -> _MarkdownRecord:
    updated: _MarkdownRecord = {
        "id": record["id"],
        "path": record["path"],
        "source_root": record["source_root"],
        "relative_path": record["relative_path"],
        "source_path": record["source_path"],
        "content_hash": record["content_hash"],
        "raw_paths": record["raw_paths"],
        "error": error,
    }
    return updated


def _untracked_items(records: list[_MarkdownRecord]) -> list[MarkdownSourceStateItem]:
    known = {(record["source_root"], record["relative_path"]) for record in records}
    items: list[MarkdownSourceStateItem] = []
    trusted_roots = {
        record["source_root"]
        for record in records
        if "error" not in record and _classify_record(record)["state"] in {"current", "modified"}
    }
    for source_root in sorted(trusted_roots):
        root_path = Path(source_root)
        if root_path.is_symlink() or not root_path.is_dir():
            continue
        for source in discover_markdown_sources(root_path, source_root=root_path):
            if (source.source_root.as_posix(), source.relative_path) in known:
                continue
            PrivacyGate().ensure_allowed_source(source.path)
            items.append(
                {
                    "state": "untracked",
                    "source_root": source.source_root.as_posix(),
                    "relative_path": source.relative_path,
                    "source_path": source.path.as_posix(),
                    "stored_content_hash": None,
                    "current_content_hash": _sha256_file(source.path),
                }
            )
    return items


def _raw_reference_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted((root / "normalized").rglob("*.json"), key=lambda item: item.as_posix()):
        try:
            payload = _load_json_object(path)
        except json.JSONDecodeError:
            continue
        for raw_path in _raw_paths(payload):
            counts[raw_path] = counts.get(raw_path, 0) + 1
    return counts


def _raw_paths(payload: dict[str, object]) -> list[str]:
    paths: list[str] = []
    for raw_ref in raw_refs_from_record(payload):
        raw_path = raw_ref.get("path")
        if isinstance(raw_path, str):
            safe_path = _safe_zone_path(raw_path, zone="raw")
            if safe_path is not None:
                paths.append(safe_path)
    return sorted(set(paths))


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): value for key, value in payload.items()} if isinstance(payload, dict) else {}


def _delete_candidates(root: Path, candidates: list[SourcePruneCandidate]) -> list[str]:
    deleted: list[str] = []
    for candidate in candidates:
        allowed_zone = (
            "normalized/markdown/documents"
            if candidate["kind"] == "normalized_markdown_record"
            else "raw"
        )
        target = _zone_file_path(root, candidate["path"], zone=allowed_zone)
        if target is None:
            continue
        target.unlink()
        deleted.append(candidate["path"])
    return deleted


def _write_tombstone(root: Path, candidates: list[SourcePruneCandidate], deleted: list[str]) -> Path:
    tombstone_path = root / "index" / "source-prune-tombstones.json"
    existing = _read_tombstones(tombstone_path)
    existing.append({"pruned_at": isoformat_utc(None), "candidates": candidates, "deleted": deleted})
    _ = atomic_write_json(tombstone_path, existing)
    return tombstone_path


def _read_tombstones(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [entry for entry in payload if isinstance(entry, dict)] if isinstance(payload, list) else []


def _prune_result(
    *,
    root: Path,
    dry_run: bool,
    candidates: list[SourcePruneCandidate],
    deleted: list[str],
    tombstone_path: Path | None,
    rebuild: dict[str, object] | None,
) -> SourcePruneResult:
    return {
        "root": root.as_posix(),
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "deleted_count": len(deleted),
        "candidates": candidates,
        "deleted": deleted,
        "tombstone_path": relative_to_root(root, tombstone_path) if tombstone_path else None,
        "rebuild": rebuild,
    }


def _source_metadata_error(
    *,
    source_root: str,
    relative_path: str,
    stored_source_path: str | None,
) -> str | None:
    root_path = Path(source_root).expanduser()
    if not root_path.is_absolute():
        return "source_root must be absolute"
    if _unsafe_relative_path(relative_path):
        return "relative_path must stay inside source_root"
    source_path = Path(_source_path_from_identity(source_root, relative_path))
    if source_path.suffix.lower() not in MARKDOWN_SUFFIXES:
        return "relative_path must point to a Markdown file"
    if stored_source_path is None:
        return "source_path is required"
    try:
        resolved_root = root_path.resolve(strict=False)
        expected_path = source_path.resolve(strict=False)
        stored_path = Path(stored_source_path).expanduser().resolve(strict=False)
        _ = expected_path.relative_to(resolved_root)
    except (OSError, ValueError):
        return "source_path must stay inside source_root"
    if stored_path != expected_path:
        return "source_path must match source_root plus relative_path"
    return None


def _source_path_from_identity(source_root: str, relative_path: str) -> str:
    return (Path(source_root).expanduser() / relative_path).as_posix()


def _unsafe_relative_path(value: str) -> bool:
    normalized = normpath(value.strip())
    return normalized in {".", ".."} or normalized.startswith("../") or Path(normalized).is_absolute()


def _safe_zone_path(value: str, *, zone: str) -> str | None:
    normalized = normpath(value.strip())
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        return None
    path = Path(normalized)
    zone_path = Path(zone)
    if path.is_absolute() or ".." in path.parts:
        return None
    if path == zone_path or zone_path not in path.parents:
        return None
    return path.as_posix()


def _zone_file_path(root: Path, value: str, *, zone: str) -> Path | None:
    safe_path = _safe_zone_path(value, zone=zone)
    if safe_path is None:
        return None
    zone_root = (root / zone).resolve(strict=False)
    target = (root / safe_path).resolve(strict=False)
    try:
        _ = target.relative_to(zone_root)
    except ValueError:
        return None
    if target.is_symlink() or not target.is_file():
        return None
    return target


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _string_value(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _normalize_source_root(path: Path) -> str:
    return path.expanduser().resolve(strict=True).as_posix()


def _item_sort_key(item: MarkdownSourceStateItem) -> tuple[int, str, str]:
    return (_state_order().index(item["state"]), item["source_root"], item["relative_path"])


def _state_order() -> tuple[MarkdownSourceState, ...]:
    return ("invalid", "modified", "missing", "untracked", "current")


def _stale_states() -> tuple[MarkdownSourceState, ...]:
    return ("invalid", "modified", "missing", "untracked")
