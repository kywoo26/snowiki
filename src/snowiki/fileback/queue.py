from __future__ import annotations

import json
from pathlib import Path

from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_json,
    isoformat_utc,
    relative_to_root,
)

from .models import (
    FILEBACK_PROPOSAL_ID_PATTERN,
    QUEUE_VERSION,
    FilebackProposal,
    QueuedFilebackProposal,
    QueuedFilebackResult,
    QueuedFilebackSummary,
    require_text,
    stringify_mapping,
)
from .proposal import coerce_fileback_proposal, validate_proposal_schema

PENDING_QUEUE_STATUS = "pending"
QUEUED_DECISION = "queued"
DEFAULT_QUEUE_IMPACT = "medium"
DEFAULT_QUEUE_REASONS = ("auto_apply_not_implemented",)


def pending_proposals_dir(root: Path) -> Path:
    return StoragePaths(root).queue_proposals / PENDING_QUEUE_STATUS


def pending_proposal_path(root: Path, proposal_id: str) -> Path:
    _validate_queue_proposal_id(proposal_id)
    return pending_proposals_dir(root) / f"{proposal_id}.json"


def queue_fileback_proposal(
    root: Path,
    proposal: FilebackProposal,
    *,
    queued_at: str | None = None,
) -> QueuedFilebackResult:
    """Persist a pending fileback proposal under the Snowiki runtime root."""
    resolved_root = root.expanduser().resolve()
    validate_proposal_schema(proposal)
    envelope = build_queue_envelope(
        resolved_root,
        proposal,
        queued_at=queued_at,
    )
    target = pending_proposal_path(resolved_root, proposal["proposal_id"])
    written_path = atomic_write_json(target, envelope)
    return {
        "queue_version": envelope["queue_version"],
        "proposal_id": envelope["proposal_id"],
        "queued_at": envelope["queued_at"],
        "status": envelope["status"],
        "decision": envelope["decision"],
        "impact": envelope["impact"],
        "requires_human_review": envelope["requires_human_review"],
        "reasons": envelope["reasons"],
        "proposal_path": relative_to_root(resolved_root, written_path),
    }


def list_queued_fileback_proposals(root: Path) -> list[QueuedFilebackSummary]:
    resolved_root = root.expanduser().resolve()
    queue_dir = pending_proposals_dir(resolved_root)
    if not queue_dir.exists():
        return []
    proposals: list[QueuedFilebackSummary] = []
    for path in sorted(queue_dir.glob("*.json"), key=lambda candidate: candidate.as_posix()):
        envelope = load_queued_fileback_proposal(path)
        proposals.append(
            {
                "proposal_id": envelope["proposal_id"],
                "queued_at": envelope["queued_at"],
                "status": envelope["status"],
                "decision": envelope["decision"],
                "impact": envelope["impact"],
                "requires_human_review": envelope["requires_human_review"],
                "reasons": envelope["reasons"],
                "proposal_path": relative_to_root(resolved_root, path),
                "target": envelope["proposal"]["target"],
                "summary": envelope["proposal"]["draft"]["summary"],
            }
        )
    return proposals


def load_queued_fileback_proposal(path: Path) -> QueuedFilebackProposal:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return coerce_queued_fileback_proposal(payload)


def build_queue_envelope(
    root: Path,
    proposal: FilebackProposal,
    *,
    queued_at: str | None = None,
) -> QueuedFilebackProposal:
    return {
        "queue_version": QUEUE_VERSION,
        "proposal_id": proposal["proposal_id"],
        "queued_at": isoformat_utc(queued_at),
        "root": root.as_posix(),
        "status": PENDING_QUEUE_STATUS,
        "decision": QUEUED_DECISION,
        "impact": DEFAULT_QUEUE_IMPACT,
        "requires_human_review": True,
        "reasons": list(DEFAULT_QUEUE_REASONS),
        "proposal": proposal,
    }


def coerce_queued_fileback_proposal(value: object) -> QueuedFilebackProposal:
    payload = stringify_mapping(value)
    queue_version = payload.get("queue_version")
    if isinstance(queue_version, bool) or queue_version != QUEUE_VERSION:
        raise ValueError(f"unsupported fileback queue version: {queue_version}")
    proposal_id = str(payload.get("proposal_id", ""))
    _validate_queue_proposal_id(proposal_id)
    proposal_value = payload.get("proposal")
    proposal = coerce_fileback_proposal(stringify_mapping(proposal_value))
    validate_proposal_schema(proposal)
    if proposal["proposal_id"] != proposal_id:
        raise ValueError("queued proposal id does not match embedded proposal")
    queued_at = require_text(str(payload.get("queued_at", "")), field_name="queued_at")
    root = require_text(str(payload.get("root", "")), field_name="root")
    status = _require_literal(
        payload.get("status"),
        field_name="status",
        expected=PENDING_QUEUE_STATUS,
    )
    decision = _require_literal(
        payload.get("decision"),
        field_name="decision",
        expected=QUEUED_DECISION,
    )
    impact = _require_literal(
        payload.get("impact"),
        field_name="impact",
        expected=DEFAULT_QUEUE_IMPACT,
    )
    requires_human_review = payload.get("requires_human_review")
    if requires_human_review is not True:
        raise ValueError("requires_human_review must be true")
    reasons = payload.get("reasons")
    if not isinstance(reasons, list):
        reasons = []
    normalized_reasons = [
        reason.strip() for reason in reasons if isinstance(reason, str) and reason.strip()
    ]
    return {
        "queue_version": QUEUE_VERSION,
        "proposal_id": proposal_id,
        "queued_at": queued_at,
        "root": root,
        "status": status,
        "decision": decision,
        "impact": impact,
        "requires_human_review": True,
        "reasons": normalized_reasons,
        "proposal": proposal,
    }


def _validate_queue_proposal_id(proposal_id: str) -> None:
    if FILEBACK_PROPOSAL_ID_PATTERN.fullmatch(proposal_id) is None:
        raise ValueError("proposal_id must match fileback-proposal-<16 lowercase hex chars>")


def _require_literal(value: object, *, field_name: str, expected: str) -> str:
    normalized = require_text(str(value or ""), field_name=field_name)
    if normalized != expected:
        raise ValueError(f"{field_name} must be {expected}")
    return normalized
