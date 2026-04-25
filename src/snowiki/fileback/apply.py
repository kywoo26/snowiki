from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from snowiki.config import resolve_snowiki_root
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_bytes,
    ensure_utc_datetime,
    isoformat_utc,
    relative_to_root,
)

from .evidence import dedupe_supporting_raw_refs, resolve_evidence
from .models import (
    FILEBACK_RECORD_TYPE,
    FILEBACK_SOURCE_TYPE,
    ProposedWriteSet,
)
from .payload import build_proposed_write_set, normalized_store_payload
from .proposal import (
    build_proposal_id,
    build_target,
    extract_fileback_proposal,
    validate_proposal_root,
    validate_proposal_schema,
)


def apply_fileback_proposal(root: Path, reviewed_payload: object) -> dict[str, Any]:
    """Persist a reviewed fileback proposal and rebuild compiled output."""
    resolved_root = resolve_snowiki_root(root)
    proposal = extract_fileback_proposal(reviewed_payload)
    validate_proposal_root(reviewed_payload, resolved_root)
    validate_proposal_schema(proposal)

    draft = proposal["draft"]
    requested_paths = proposal["evidence"]["requested_paths"]
    expected_proposal_id = build_proposal_id(
        question=draft["question"],
        answer_markdown=draft["answer_markdown"],
        summary=draft["summary"],
        requested_paths=requested_paths,
    )
    if proposal["proposal_id"] != expected_proposal_id:
        raise ValueError("reviewed proposal id no longer matches its draft and evidence")

    target = build_target(draft["question"])
    if proposal["target"] != target:
        raise ValueError("proposal target no longer matches the reviewed question")

    evidence = resolve_evidence(resolved_root, requested_paths)
    proposed_write = build_proposed_write_set(
        proposal_id=proposal["proposal_id"],
        created_at=proposal["created_at"],
        draft=draft,
        target=target,
        evidence=evidence,
    )
    validate_apply_plan(proposal["apply_plan"], proposed_write)
    applied_at = isoformat_utc(None)

    write_manual_raw_note(
        resolved_root,
        relative_path=proposed_write["raw_note_path"],
        content=proposed_write["raw_note_body"],
        mtime=proposal["created_at"],
    )
    raw_ref = proposed_write["raw_ref"]

    normalized_storage = NormalizedStorage(resolved_root)
    provenance_refs = [
        raw_ref,
        *dedupe_supporting_raw_refs(evidence["supporting_raw_refs"], raw_ref["path"]),
    ]
    store_result = normalized_storage.store_record(
        source_type=FILEBACK_SOURCE_TYPE,
        record_type=FILEBACK_RECORD_TYPE,
        record_id=str(proposed_write["normalized_record"]["id"]),
        payload=normalized_store_payload(proposed_write["normalized_record"]),
        raw_ref=provenance_refs,
        recorded_at=str(proposed_write["normalized_record"]["recorded_at"]),
    )
    rebuild_result = run_rebuild_with_integrity(resolved_root)
    return {
        "root": resolved_root.as_posix(),
        "applied_at": applied_at,
        "proposal_id": proposal["proposal_id"],
        "proposal_version": proposal["proposal_version"],
        "raw_ref": raw_ref,
        "supporting_raw_ref_count": len(evidence["supporting_raw_refs"]),
        "normalized_path": store_result["path"],
        "compiled_path": target["compiled_path"],
        "rebuild": rebuild_result,
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
