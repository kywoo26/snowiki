from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from snowiki.config import resolve_snowiki_root
from snowiki.storage.zones import atomic_write_json, isoformat_utc, relative_to_root

from ..models import (
    FilebackProposal,
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
    copy_transition_metadata,
    load_validated_queued_fileback_proposal,
    queue_result,
    queue_summary,
    queue_transition_result,
    reviewed_payload_from_queue,
    transition_envelope,
)
from .policy import classify_low_risk_auto_apply
from .store import (
    find_existing_queue_state_paths,
    iter_queue_paths,
    pending_proposal_path,
    queue_proposal_path,
)
from .types import (
    ALL_QUEUE_STATUSES,
    APPLIED_QUEUE_STATUS,
    AUTO_APPLIED_DECISION,
    FAILED_QUEUE_STATUS,
    PENDING_QUEUE_STATUS,
    REJECTED_QUEUE_STATUS,
    QueueListStatus,
    QueuePolicyDecision,
    QueueStatus,
    TerminalQueueStatus,
)


def queue_fileback_proposal(
    root: Path,
    proposal: FilebackProposal,
    *,
    queued_at: str | None = None,
    policy: QueuePolicyDecision | None = None,
) -> QueuedFilebackResult:
    """Persist a pending fileback proposal under the Snowiki runtime root."""
    resolved_root = root.expanduser().resolve()
    validate_proposal_schema(proposal)
    _ensure_no_existing_state(resolved_root, proposal["proposal_id"])
    envelope = build_queue_envelope(
        resolved_root,
        proposal,
        queued_at=queued_at,
        policy=policy,
    )
    target = queue_proposal_path(resolved_root, proposal["proposal_id"], PENDING_QUEUE_STATUS)
    written_path = atomic_write_json(target, envelope)
    return queue_result(resolved_root, envelope, written_path)


def auto_apply_fileback_proposal(
    root: Path,
    proposal: FilebackProposal,
    *,
    queued_at: str | None = None,
) -> QueuedFilebackResult:
    """Queue a proposal and apply it only when runtime policy proves it low-risk."""
    resolved_root = resolve_snowiki_root(root)
    decision = classify_low_risk_auto_apply(resolved_root, proposal)
    queued = queue_fileback_proposal(
        resolved_root,
        proposal,
        queued_at=queued_at,
        policy=decision,
    )
    if decision["requires_human_review"]:
        return queued
    applied = apply_queued_fileback_proposal(
        resolved_root,
        proposal["proposal_id"],
        transition_reason="auto_apply_low_risk",
    )
    result = {key: applied[key] for key in queued}
    return cast(QueuedFilebackResult, cast(object, result))


def run_fileback_preview(
    root: Path | None,
    *,
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: tuple[str, ...],
    queue_proposal: bool = False,
    auto_apply_low_risk: bool = False,
) -> dict[str, Any]:
    if auto_apply_low_risk and not queue_proposal:
        raise ValueError("--auto-apply-low-risk requires --queue")
    preview_root = (
        resolve_snowiki_root(root)
        if queue_proposal or auto_apply_low_risk
        else resolve_preview_root(root)
    )
    proposal = build_fileback_proposal(
        preview_root,
        question=question,
        answer_markdown=answer_markdown,
        summary=summary,
        evidence_paths=evidence_paths,
    )
    if auto_apply_low_risk:
        queue_result = auto_apply_fileback_proposal(preview_root, proposal)
    elif queue_proposal:
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
    *,
    status: QueueListStatus = PENDING_QUEUE_STATUS,
) -> list[QueuedFilebackSummary]:
    resolved_root = root.expanduser().resolve()
    proposals: list[QueuedFilebackSummary] = []
    for expected_status in _statuses_for_list(status):
        for path in iter_queue_paths(resolved_root, (expected_status,)):
            envelope = load_validated_queued_fileback_proposal(
                resolved_root,
                path,
                expected_status,
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
    path = find_queued_fileback_proposal_path(resolved_root, proposal_id)
    envelope = load_validated_queued_fileback_proposal(
        resolved_root,
        path,
        _status_from_path(resolved_root, path),
        expected_proposal_id=proposal_id,
    )
    result: dict[str, object] = {**queue_summary(resolved_root, envelope, path)}
    copy_transition_metadata(envelope, result)
    if verbose:
        result["proposal"] = envelope["proposal"]
        if "result" in envelope:
            result["result"] = envelope["result"]
    return result


def apply_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
    *,
    transition_reason: str = "queue_apply",
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
    try:
        apply_result = apply_fileback_proposal(
            resolved_root,
            reviewed_payload_from_queue(envelope),
        )
    except Exception as exc:
        failed = transition_queued_fileback_proposal(
            resolved_root,
            proposal_id,
            FAILED_QUEUE_STATUS,
            transition_reason=str(exc),
            result={"ok": False, "error": {"message": str(exc)}},
        )
        raise ValueError(
            f"queued proposal {proposal_id} failed and was archived at {failed['proposal_path']}: {exc}"
        ) from exc
    return transition_queued_fileback_proposal(
        resolved_root,
        proposal_id,
        APPLIED_QUEUE_STATUS,
        transition_reason=transition_reason,
        result={"ok": True, **apply_result},
        decision=AUTO_APPLIED_DECISION
        if transition_reason == "auto_apply_low_risk"
        else envelope["decision"],
        requires_human_review=False,
    )


def reject_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
    *,
    reason: str,
) -> dict[str, Any]:
    normalized_reason = require_text(reason, field_name="reason")
    resolved_root = resolve_snowiki_root(root)
    return transition_queued_fileback_proposal(
        resolved_root,
        proposal_id,
        REJECTED_QUEUE_STATUS,
        transition_reason=normalized_reason,
        result={"ok": True, "reason": normalized_reason},
        requires_human_review=False,
    )


def transition_queued_fileback_proposal(
    root: Path,
    proposal_id: str,
    status: TerminalQueueStatus,
    *,
    transition_reason: str,
    result: dict[str, Any],
    decision: str | None = None,
    requires_human_review: bool | None = None,
) -> dict[str, Any]:
    resolved_root = root.expanduser().resolve()
    source_path = pending_proposal_path(resolved_root, proposal_id)
    existing_paths = find_existing_queue_state_paths(resolved_root, proposal_id)
    if existing_paths != [source_path]:
        existing_states = ", ".join(
            relative_to_root(resolved_root, path) for path in existing_paths
        )
        raise ValueError(
            f"queued proposal must exist only as pending before transition: {proposal_id} ({existing_states})"
        )
    envelope = load_validated_queued_fileback_proposal(
        resolved_root,
        source_path,
        PENDING_QUEUE_STATUS,
        expected_proposal_id=proposal_id,
    )
    target_path = queue_proposal_path(resolved_root, proposal_id, status)
    written_path = atomic_write_json(
        target_path,
        transition_envelope(
            envelope,
            status=status,
            transitioned_at=isoformat_utc(None),
            transition_reason=transition_reason,
            result=result,
            decision=decision,
            requires_human_review=requires_human_review,
        ),
    )
    source_path.unlink()
    return queue_transition_result(
        resolved_root,
        load_validated_queued_fileback_proposal(
            resolved_root,
            written_path,
            status,
            expected_proposal_id=proposal_id,
        ),
        written_path,
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


def _statuses_for_list(status: QueueListStatus) -> tuple[QueueStatus, ...]:
    if status == "all":
        return ALL_QUEUE_STATUSES
    return (status,)


def _status_from_path(root: Path, path: Path) -> QueueStatus:
    relative = path.relative_to(root)
    status = relative.parts[-2] if len(relative.parts) >= 2 else ""
    for known_status in ALL_QUEUE_STATUSES:
        if status == known_status:
            return known_status
    raise ValueError("queued proposal path does not include a valid queue status")
