from __future__ import annotations

from pathlib import Path
from typing import Any

from snowiki.config import resolve_snowiki_root
from snowiki.storage.zones import atomic_write_json, relative_to_root

from ..models import (
    FilebackProposal,
    QueuedFilebackProposal,
    QueuedFilebackResult,
    QueuedFilebackSummary,
    require_text,
)
from ..proposal import (
    build_fileback_proposal,
    resolve_preview_root,
    validate_proposal_schema,
)
from .codec import (
    build_fileback_preview_result,
    build_queue_envelope,
    load_validated_queued_fileback_proposal,
    queue_result,
    queue_summary,
    reviewed_payload_from_queue,
)
from .store import (
    find_existing_queue_state_paths,
    iter_pending_queue_paths,
    pending_proposal_path,
    queue_proposal_path,
)
from .types import PENDING_QUEUE_STATUS


def queue_fileback_proposal(
    root: Path,
    proposal: FilebackProposal,
    *,
    queued_at: str | None = None,
) -> QueuedFilebackResult:
    """Persist a pending fileback proposal under the Snowiki runtime root."""
    resolved_root = root.expanduser().resolve()
    validate_proposal_schema(proposal)
    _ensure_no_existing_state(resolved_root, proposal["proposal_id"])
    envelope = build_queue_envelope(
        resolved_root,
        proposal,
        queued_at=queued_at,
    )
    target = queue_proposal_path(resolved_root, proposal["proposal_id"], PENDING_QUEUE_STATUS)
    written_path = atomic_write_json(target, envelope)
    return queue_result(resolved_root, envelope, written_path)


def run_fileback_preview(
    root: Path | None,
    *,
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: tuple[str, ...],
    queue_proposal: bool = False,
) -> dict[str, Any]:
    preview_root = resolve_snowiki_root(root) if queue_proposal else resolve_preview_root(root)
    proposal = build_fileback_proposal(
        preview_root,
        question=question,
        answer_markdown=answer_markdown,
        summary=summary,
        evidence_paths=evidence_paths,
    )
    if queue_proposal:
        queue_result = queue_fileback_proposal(preview_root, proposal)
    else:
        queue_result = None
    return build_fileback_preview_result(
        root=preview_root,
        proposal=proposal,
        queue_result=queue_result,
    )


def list_queued_fileback_proposals(
    root: Path,
) -> list[QueuedFilebackSummary]:
    resolved_root = root.expanduser().resolve()
    proposals: list[QueuedFilebackSummary] = []
    for path in iter_pending_queue_paths(resolved_root):
        envelope = load_validated_queued_fileback_proposal(
            resolved_root,
            path,
            PENDING_QUEUE_STATUS,
        )
        proposals.append(queue_summary(resolved_root, envelope, path))
    return proposals


def show_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    resolved_root = root.expanduser().resolve()
    path = pending_proposal_path(resolved_root, proposal_id)
    envelope = load_validated_queued_fileback_proposal(
        resolved_root,
        path,
        PENDING_QUEUE_STATUS,
        expected_proposal_id=proposal_id,
    )
    result: dict[str, object] = {**queue_summary(resolved_root, envelope, path)}
    if verbose:
        result["proposal"] = envelope["proposal"]
    return result


def apply_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
) -> dict[str, Any]:
    from ..apply import apply_fileback_proposal

    resolved_root = resolve_snowiki_root(root)
    source_path = pending_proposal_path(resolved_root, proposal_id)
    envelope = load_validated_queued_fileback_proposal(
        resolved_root,
        source_path,
        PENDING_QUEUE_STATUS,
        expected_proposal_id=proposal_id,
    )
    apply_result = apply_fileback_proposal(
        resolved_root,
        reviewed_payload_from_queue(envelope),
    )
    source_path.unlink()
    return _queue_completion_result(
        resolved_root,
        envelope,
        source_path,
        status="applied",
        result={"ok": True, **apply_result},
    )


def reject_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
    *,
    reason: str,
) -> dict[str, Any]:
    normalized_reason = require_text(reason, field_name="reason")
    resolved_root = resolve_snowiki_root(root)
    source_path = pending_proposal_path(resolved_root, proposal_id)
    envelope = load_validated_queued_fileback_proposal(
        resolved_root,
        source_path,
        PENDING_QUEUE_STATUS,
        expected_proposal_id=proposal_id,
    )
    source_path.unlink()
    return _queue_completion_result(
        resolved_root,
        envelope,
        source_path,
        status="rejected",
        result={"ok": True, "reason": normalized_reason},
        transition_reason=normalized_reason,
    )


def find_queued_fileback_proposal_path(root: Path, proposal_id: str) -> Path:
    matches = find_existing_queue_state_paths(root, proposal_id)
    if not matches:
        raise ValueError(f"queued proposal not found: {proposal_id}")
    if len(matches) > 1:
        raise ValueError(f"queued proposal has multiple state files: {proposal_id}")
    return matches[0]


def _ensure_no_existing_state(root: Path, proposal_id: str) -> None:
    existing_paths = find_existing_queue_state_paths(root, proposal_id)
    if not existing_paths:
        return
    existing_states = ", ".join(relative_to_root(root, path) for path in existing_paths)
    raise ValueError(
        f"queued proposal already exists in queue state: {proposal_id} ({existing_states})"
    )


def _queue_completion_result(
    root: Path,
    envelope: QueuedFilebackProposal,
    source_path: Path,
    *,
    status: str,
    result: dict[str, Any],
    transition_reason: str | None = None,
) -> dict[str, Any]:
    summary = queue_summary(root, envelope, source_path)
    completion: dict[str, Any] = {
        **summary,
        "queue_version": envelope["queue_version"],
        "status": status,
        "deleted_proposal_path": relative_to_root(root, source_path),
        "result": result,
    }
    if transition_reason is not None:
        completion["transition_reason"] = transition_reason
    return completion
