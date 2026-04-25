from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

GARDENING_PROPOSAL_VERSION = "garden.source.v1"

GardeningProposalType = Literal[
    "source_rename_candidate",
    "manual_gardening_required",
]
GardeningRisk = Literal["low", "medium", "high", "manual"]


class GardeningEvidence(TypedDict):
    kind: str
    state: str
    source_root: str
    relative_path: str
    source_path: str
    content_hash: str | None
    normalized_path: NotRequired[str]
    record_id: NotRequired[str]
    error: NotRequired[str]


class GardeningProposal(TypedDict):
    proposal_id: str
    proposal_version: str
    proposal_type: GardeningProposalType
    risk: GardeningRisk
    apply_supported: bool
    evidence: list[GardeningEvidence]
    recommended_action: str
    manual_reason: str | None


class SourceGardeningReport(TypedDict):
    root: str
    dry_run: bool
    proposal_count: int
    proposals: list[GardeningProposal]
