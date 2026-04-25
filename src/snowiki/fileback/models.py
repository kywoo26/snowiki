from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

PROPOSAL_VERSION = 1
QUEUE_VERSION = 1
FILEBACK_SOURCE_TYPE = "manual-question"
FILEBACK_RECORD_TYPE = "question"
FILEBACK_PROPOSAL_ID_PATTERN = re.compile(r"^fileback-proposal-[0-9a-f]{16}$")


class RawRefDict(TypedDict):
    sha256: str
    path: str
    size: int
    mtime: str


class EvidenceResolution(TypedDict):
    requested_paths: list[str]
    resolved_paths: dict[str, list[str]]
    supporting_record_ids: list[str]
    supporting_raw_refs: list[RawRefDict]


class FilebackDraft(TypedDict):
    question: str
    answer_markdown: str
    summary: str


class FilebackTarget(TypedDict):
    title: str
    slug: str
    compiled_path: str


class FilebackProposal(TypedDict):
    proposal_id: str
    proposal_version: int
    created_at: str
    target: FilebackTarget
    draft: FilebackDraft
    evidence: EvidenceResolution
    derivation: dict[str, Any]
    apply_plan: dict[str, Any]


class QueuedFilebackProposal(TypedDict):
    queue_version: int
    proposal_id: str
    queued_at: str
    root: str
    status: str
    decision: str
    impact: str
    requires_human_review: bool
    reasons: list[str]
    proposal: FilebackProposal
    previous_status: NotRequired[str]
    transitioned_at: NotRequired[str]
    transition_reason: NotRequired[str]
    result: NotRequired[dict[str, Any]]


class QueuedFilebackResult(TypedDict):
    queue_version: int
    proposal_id: str
    queued_at: str
    status: str
    decision: str
    impact: str
    requires_human_review: bool
    reasons: list[str]
    proposal_path: str


class QueuedFilebackSummary(TypedDict):
    proposal_id: str
    queued_at: str
    status: str
    decision: str
    impact: str
    requires_human_review: bool
    reasons: list[str]
    proposal_path: str
    target: FilebackTarget
    summary: str
    evidence_requested_paths: list[str]


class ProposedWriteSet(TypedDict):
    raw_note_body: str
    raw_note_path: str
    raw_ref: RawRefDict
    normalized_record: dict[str, Any]
    normalized_path: str


class LoadedNormalizedRecord(TypedDict):
    id: str
    path: str
    raw_refs: list[RawRefDict]


def require_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def stringify_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("expected a mapping")
    return {str(key): item for key, item in value.items()}


def require_mapping(value: Mapping[str, object], field_name: str) -> dict[str, object]:
    field_value = value.get(field_name)
    if not isinstance(field_value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return {str(key): item for key, item in field_value.items()}


def require_exact_int_field(value: Mapping[str, object], field_name: str) -> int:
    field_value = value.get(field_name)
    if isinstance(field_value, bool) or not isinstance(field_value, int):
        raise ValueError(f"{field_name} must be an integer")
    return field_value


def require_string_field(value: Mapping[str, object], field_name: str) -> str:
    field_value = value.get(field_name)
    if not isinstance(field_value, str):
        raise ValueError(f"{field_name} is required")
    return field_value


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def coerce_int_like_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"expected integer-compatible value, got {type(value).__name__}")


def coerce_raw_ref(value: Mapping[str, object]) -> RawRefDict:
    return {
        "sha256": str(value["sha256"]),
        "path": str(value["path"]),
        "size": coerce_int_like_value(value["size"]),
        "mtime": str(value["mtime"]),
    }


def is_raw_ref_mapping(value: Mapping[str, object]) -> bool:
    return {"sha256", "path", "size", "mtime"}.issubset(value)
