from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

from snowiki.markdown.source_state import (
    collect_markdown_source_state,
    raw_reference_counts,
    zone_file_path,
)
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.storage.zones import atomic_write_json, isoformat_utc, relative_to_root


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
    raw_counts = raw_reference_counts(resolved_root)
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
            target = zone_file_path(resolved_root, raw_path, zone="raw")
            if target is None or raw_counts.get(raw_path) != 1:
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


def _delete_candidates(root: Path, candidates: list[SourcePruneCandidate]) -> list[str]:
    deleted: list[str] = []
    for candidate in candidates:
        allowed_zone = (
            "normalized/markdown/documents"
            if candidate["kind"] == "normalized_markdown_record"
            else "raw"
        )
        target = zone_file_path(root, candidate["path"], zone=allowed_zone)
        if target is None:
            continue
        target.unlink()
        deleted.append(candidate["path"])
    return deleted


def _write_tombstone(
    root: Path, candidates: list[SourcePruneCandidate], deleted: list[str]
) -> Path:
    tombstone_path = root / "index" / "source-prune-tombstones.json"
    existing = _read_tombstones(tombstone_path)
    existing.append({"pruned_at": isoformat_utc(None), "candidates": candidates, "deleted": deleted})
    _ = atomic_write_json(tombstone_path, existing)
    return tombstone_path


def _read_tombstones(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(payload, list):
        return []
    return [cast(dict[str, object], entry) for entry in payload if isinstance(entry, dict)]


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
