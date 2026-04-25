from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from snowiki.gardening.models import (
    GARDENING_PROPOSAL_VERSION,
    GardeningEvidence,
    GardeningProposal,
    GardeningProposalType,
    GardeningRisk,
    SourceGardeningReport,
)
from snowiki.markdown.source_state import (
    MarkdownSourceStateItem,
    collect_markdown_source_state,
)


def collect_source_gardening_proposals(root: str | Path) -> SourceGardeningReport:
    """Build reviewable source gardening proposals without mutating storage."""
    resolved_root = Path(root).expanduser().resolve()
    report = collect_markdown_source_state(resolved_root)
    items = report["items"]
    proposals = _source_rename_proposals(items)
    proposal_keys = _proposal_item_keys(proposals)
    proposals.extend(_manual_proposals(items, proposal_keys))
    proposals.sort(key=lambda proposal: proposal["proposal_id"])
    return {
        "root": resolved_root.as_posix(),
        "dry_run": True,
        "proposal_count": len(proposals),
        "proposals": proposals,
    }


def _source_rename_proposals(
    items: list[MarkdownSourceStateItem],
) -> list[GardeningProposal]:
    proposals: list[GardeningProposal] = []
    missing_items = [item for item in items if item["state"] == "missing"]
    untracked_items = [item for item in items if item["state"] == "untracked"]
    match_counts = _rename_match_counts(missing_items, untracked_items)
    for missing in missing_items:
        stored_hash = missing["stored_content_hash"]
        matches = [
            item
            for item in untracked_items
            if item["source_root"] == missing["source_root"]
            and item["current_content_hash"] == stored_hash
        ]
        if len(matches) != 1 or match_counts[_item_key(matches[0])] != 1:
            continue
        proposals.append(
            _proposal(
                proposal_type="source_rename_candidate",
                risk="low",
                apply_supported=False,
                evidence=[_evidence("missing_record", missing), _evidence("untracked_source", matches[0])],
                recommended_action="reingest_new_source_then_review_prune_old_record",
                manual_reason=(
                    "apply is intentionally not supported in the first gardening slice; "
                    "review the rename evidence, reingest the untracked source, then run source prune dry-run"
                ),
            )
        )
    return proposals


def _rename_match_counts(
    missing_items: list[MarkdownSourceStateItem],
    untracked_items: list[MarkdownSourceStateItem],
) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = {}
    for missing in missing_items:
        stored_hash = missing["stored_content_hash"]
        for untracked in untracked_items:
            if (
                untracked["source_root"] == missing["source_root"]
                and untracked["current_content_hash"] == stored_hash
            ):
                key = _item_key(untracked)
                counts[key] = counts.get(key, 0) + 1
    return counts


def _manual_proposals(
    items: list[MarkdownSourceStateItem],
    proposal_keys: set[tuple[str, str, str]],
) -> list[GardeningProposal]:
    proposals: list[GardeningProposal] = []
    for item in items:
        key = _item_key(item)
        if key in proposal_keys or item["state"] == "current":
            continue
        manual = _manual_action(item)
        proposals.append(
            _proposal(
                proposal_type="manual_gardening_required",
                risk="manual",
                apply_supported=False,
                evidence=[_evidence("source_state", item)],
                recommended_action=manual[0],
                manual_reason=manual[1],
            )
        )
    return proposals


def _manual_action(item: MarkdownSourceStateItem) -> tuple[str, str]:
    state = item["state"]
    if state == "modified":
        return (
            "reingest_modified_source",
            "source content changed since ingest; reingest before cleanup proposals",
        )
    if state == "missing":
        return (
            "review_missing_source_for_prune_or_rename",
            "missing source did not have exactly one same-hash untracked rename candidate",
        )
    if state == "untracked":
        return (
            "review_untracked_source_for_ingest",
            "untracked source is not part of a safe exact-hash rename candidate",
        )
    if state == "invalid":
        return (
            "repair_invalid_source_metadata",
            item.get("error", "source metadata is invalid and needs manual repair"),
        )
    return ("no_action", "no gardening action is required")


def _proposal(
    *,
    proposal_type: GardeningProposalType,
    risk: GardeningRisk,
    apply_supported: bool,
    evidence: list[GardeningEvidence],
    recommended_action: str,
    manual_reason: str | None,
) -> GardeningProposal:
    body = {
        "proposal_version": GARDENING_PROPOSAL_VERSION,
        "proposal_type": proposal_type,
        "risk": risk,
        "apply_supported": apply_supported,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "manual_reason": manual_reason,
    }
    proposal: GardeningProposal = {
        "proposal_id": _proposal_id(body),
        "proposal_version": GARDENING_PROPOSAL_VERSION,
        "proposal_type": proposal_type,
        "risk": risk,
        "apply_supported": apply_supported,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "manual_reason": manual_reason,
    }
    return proposal


def _proposal_id(body: Mapping[str, object]) -> str:
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]
    return f"garden-{digest}"


def _evidence(kind: str, item: MarkdownSourceStateItem) -> GardeningEvidence:
    evidence: GardeningEvidence = {
        "kind": kind,
        "state": item["state"],
        "source_root": item["source_root"],
        "relative_path": item["relative_path"],
        "source_path": item["source_path"],
        "content_hash": item["current_content_hash"] or item["stored_content_hash"],
    }
    normalized_path = item.get("normalized_path")
    if normalized_path is not None:
        evidence["normalized_path"] = normalized_path
    record_id = item.get("record_id")
    if record_id is not None:
        evidence["record_id"] = record_id
    error = item.get("error")
    if error is not None:
        evidence["error"] = error
    return evidence


def _proposal_item_keys(proposals: list[GardeningProposal]) -> set[tuple[str, str, str]]:
    return {
        (evidence["state"], evidence["source_root"], evidence["relative_path"])
        for proposal in proposals
        for evidence in proposal["evidence"]
    }


def _item_key(item: MarkdownSourceStateItem) -> tuple[str, str, str]:
    return (item["state"], item["source_root"], item["relative_path"])
