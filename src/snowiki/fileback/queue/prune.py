from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from snowiki.storage.zones import relative_to_root

from .codec import (
    load_queued_fileback_proposal,
    load_validated_queued_fileback_proposal,
)
from .store import iter_queue_paths
from .types import (
    DEFAULT_KEEP_TERMINAL,
    TERMINAL_QUEUE_STATUSES,
    QueuePruneResult,
    TerminalQueueStatus,
)


def prune_queued_fileback_proposals(
    root: Path,
    *,
    status: Literal["applied", "rejected", "failed", "all"],
    keep: int | None = None,
    older_than: timedelta | None = None,
    dry_run: bool = True,
) -> QueuePruneResult:
    if keep is not None and keep < 0:
        raise ValueError("keep must be zero or greater")
    resolved_root = root.expanduser().resolve()
    effective_keep = DEFAULT_KEEP_TERMINAL if keep is None and older_than is None else keep
    statuses = TERMINAL_QUEUE_STATUSES if status == "all" else (status,)
    candidates: list[Path] = []
    retained_count = 0
    cutoff = datetime.now(tz=UTC) - older_than if older_than is not None else None

    for current_status in statuses:
        paths = [
            path
            for path in iter_queue_paths(resolved_root, (current_status,))
            if _is_valid_prune_candidate(resolved_root, path, current_status)
        ]
        ordered = sorted(paths, key=_queue_path_timestamp, reverse=True)
        protected = set(ordered[:effective_keep]) if effective_keep is not None else set()
        retained_count += len(protected)
        candidate_pool = ordered[effective_keep:] if effective_keep is not None else ordered
        for path in candidate_pool:
            if cutoff is not None and _queue_path_timestamp(path) >= cutoff:
                retained_count += 1
                continue
            if path not in protected:
                candidates.append(path)

    bytes_considered = sum(path.stat().st_size for path in candidates if path.exists())
    deleted = _delete_candidates(candidates) if not dry_run else []
    return {
        "root": resolved_root.as_posix(),
        "statuses": list(statuses),
        "dry_run": dry_run,
        "keep": effective_keep,
        "older_than": _format_timedelta(older_than),
        "candidate_count": len(candidates),
        "deleted_count": len(deleted),
        "retained_count": retained_count,
        "bytes_considered": bytes_considered,
        "bytes_deleted": bytes_considered if not dry_run else 0,
        "candidates": [relative_to_root(resolved_root, path) for path in candidates],
        "deleted": [relative_to_root(resolved_root, path) for path in deleted],
    }


def _delete_candidates(candidates: list[Path]) -> list[Path]:
    deleted: list[Path] = []
    for path in candidates:
        if path.exists():
            path.unlink()
            deleted.append(path)
    return deleted


def _is_valid_prune_candidate(
    root: Path, path: Path, expected_status: TerminalQueueStatus
) -> bool:
    try:
        envelope = load_validated_queued_fileback_proposal(root, path, expected_status)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return envelope["proposal_id"] == path.stem and envelope["status"] == expected_status


def _queue_path_timestamp(path: Path) -> datetime:
    envelope = load_queued_fileback_proposal(path)
    value = envelope.get("transitioned_at") or envelope["queued_at"]
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


def _format_timedelta(value: timedelta | None) -> str | None:
    if value is None:
        return None
    seconds = int(value.total_seconds())
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    return f"{seconds}s"
