from __future__ import annotations

from pathlib import Path

from ..models import FILEBACK_RECORD_TYPE, FILEBACK_SOURCE_TYPE, FilebackProposal
from ..proposal import validate_proposal_schema
from .codec import queued_policy
from .store import is_inside_root
from .types import (
    AUTO_APPLIED_DECISION,
    DEFAULT_QUEUE_IMPACT,
    LOW_RISK_IMPACT,
    QUEUED_DECISION,
    QueuePolicyDecision,
)


def classify_low_risk_auto_apply(root: Path, proposal: FilebackProposal) -> QueuePolicyDecision:
    """Return runtime-owned auto-apply policy for a fileback proposal."""
    reasons: list[str] = []
    try:
        validate_proposal_schema(proposal)
    except ValueError as exc:
        return queued_policy(f"invalid_proposal:{exc}")

    apply_plan = proposal["apply_plan"]
    _require_apply_plan_literals(apply_plan, reasons)
    _check_write_path(root, apply_plan.get("raw_note_path"), "raw_note_path", reasons)
    _check_write_path(root, apply_plan.get("normalized_path"), "normalized_path", reasons)
    _check_write_path(
        root,
        proposal["target"]["compiled_path"],
        "compiled_path",
        reasons,
        missing_reason="missing_compiled_path",
        out_of_root_reason="out_of_root_compiled_path",
        collision_reason="compiled_target_already_exists",
    )
    _check_evidence_paths(root, proposal, reasons)

    if reasons:
        return {
            "decision": QUEUED_DECISION,
            "impact": DEFAULT_QUEUE_IMPACT,
            "requires_human_review": True,
            "reasons": reasons,
        }
    return {
        "decision": AUTO_APPLIED_DECISION,
        "impact": LOW_RISK_IMPACT,
        "requires_human_review": False,
        "reasons": ["runtime_low_risk_policy_passed"],
    }


def _require_apply_plan_literals(apply_plan: dict[str, object], reasons: list[str]) -> None:
    if apply_plan.get("source_type") != FILEBACK_SOURCE_TYPE:
        reasons.append("unsupported_source_type")
    if apply_plan.get("record_type") != FILEBACK_RECORD_TYPE:
        reasons.append("unsupported_record_type")
    if apply_plan.get("rebuild_required") is not True:
        reasons.append("missing_checked_rebuild")


def _check_write_path(
    root: Path,
    value: object,
    field_name: str,
    reasons: list[str],
    *,
    missing_reason: str | None = None,
    out_of_root_reason: str | None = None,
    collision_reason: str | None = None,
) -> None:
    if not isinstance(value, str) or not value.strip():
        reasons.append(missing_reason or f"missing_{field_name}")
        return
    target_path = (root / value).resolve()
    if not is_inside_root(root, target_path):
        reasons.append(out_of_root_reason or f"out_of_root_{field_name}")
    elif target_path.exists():
        reasons.append(collision_reason or f"colliding_{field_name}")


def _check_evidence_paths(
    root: Path, proposal: FilebackProposal, reasons: list[str]
) -> None:
    for evidence_path in proposal["evidence"]["requested_paths"]:
        resolved = (root / evidence_path).resolve()
        if not is_inside_root(root, resolved):
            reasons.append("out_of_root_evidence")
            break
