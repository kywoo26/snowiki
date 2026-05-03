from __future__ import annotations

import importlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_bytes,
    ensure_utc_datetime,
    relative_to_root,
)

from .models import (
    FILEBACK_RECORD_TYPE,
    FILEBACK_SOURCE_TYPE,
    ProposedWriteSet,
)


def apply_fileback_proposal(root: Path, reviewed_payload: object) -> dict[str, Any]:
    """Persist a reviewed fileback proposal through the mutation domain."""
    domain_module = importlib.import_module("snowiki.operations.domain")
    service_module = importlib.import_module("snowiki.operations.service")

    outcome = service_module.OperationPipeline.from_root(root).apply_reviewed_fileback(
        domain_module.ReviewedFilebackOperation(
            root=root,
            reviewed_payload=reviewed_payload,
        )
    )
    if not outcome.accepted:
        if outcome.failure is not None:
            raise ValueError(outcome.failure.message)
        raise ValueError("reviewed fileback mutation was not accepted")
    if outcome.rebuild is None:
        raise ValueError("reviewed fileback mutation did not produce rebuild output")

    detail = dict(outcome.detail or {})
    return {
        "root": outcome.root.as_posix(),
        "applied_at": detail["applied_at"],
        "proposal_id": detail["proposal_id"],
        "proposal_version": detail["proposal_version"],
        "raw_ref": detail["raw_ref"],
        "supporting_raw_ref_count": detail["supporting_raw_ref_count"],
        "normalized_path": detail["normalized_path"],
        "compiled_path": detail["compiled_path"],
        "rebuild": service_module.materialization_outcome_payload(outcome.rebuild),
    }


def validate_apply_plan(
    apply_plan: Mapping[str, Any], proposed_write: ProposedWriteSet
) -> None:
    expected = {
        "source_type": FILEBACK_SOURCE_TYPE,
        "record_type": FILEBACK_RECORD_TYPE,
        "record_id": proposed_write["normalized_record"]["id"],
        "raw_note_path": proposed_write["raw_note_path"],
        "normalized_path": proposed_write["normalized_path"],
        "proposed_raw_note_body": proposed_write["raw_note_body"],
        "proposed_normalized_record_payload": proposed_write["normalized_record"],
        "rebuild_required": True,
    }
    if dict(apply_plan) != expected:
        raise ValueError("reviewed apply plan no longer matches the proposed write set")


def write_manual_raw_note(
    root: Path, *, relative_path: str, content: str, mtime: str
) -> None:
    storage_paths = StoragePaths(root)
    target = (storage_paths.root / relative_path).resolve()
    try:
        _ = relative_to_root(storage_paths.root.resolve(), target)
    except ValueError as exc:
        raise ValueError("manual question raw path must stay inside the Snowiki root") from exc
    _ = atomic_write_bytes(target, content.encode("utf-8"))
    timestamp = ensure_utc_datetime(mtime).timestamp()
    os.utime(target, (timestamp, timestamp))
