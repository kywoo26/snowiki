from __future__ import annotations

from typing import Literal, TypedDict

QueueStatus = Literal["pending", "applied", "rejected", "failed"]
QueueListStatus = Literal["pending", "applied", "rejected", "failed", "all"]
TerminalQueueStatus = Literal["applied", "rejected", "failed"]

PENDING_QUEUE_STATUS: QueueStatus = "pending"
APPLIED_QUEUE_STATUS: TerminalQueueStatus = "applied"
REJECTED_QUEUE_STATUS: TerminalQueueStatus = "rejected"
FAILED_QUEUE_STATUS: TerminalQueueStatus = "failed"
ALL_QUEUE_STATUSES: tuple[QueueStatus, ...] = (
    PENDING_QUEUE_STATUS,
    APPLIED_QUEUE_STATUS,
    REJECTED_QUEUE_STATUS,
    FAILED_QUEUE_STATUS,
)
TERMINAL_QUEUE_STATUSES: tuple[TerminalQueueStatus, ...] = (
    APPLIED_QUEUE_STATUS,
    REJECTED_QUEUE_STATUS,
    FAILED_QUEUE_STATUS,
)

QUEUED_DECISION = "queued"
AUTO_APPLIED_DECISION = "auto_applied"
LOW_RISK_IMPACT = "low"
DEFAULT_QUEUE_IMPACT = "medium"
DEFAULT_KEEP_TERMINAL = 50


class QueuePolicyDecision(TypedDict):
    decision: str
    impact: str
    requires_human_review: bool
    reasons: list[str]


class QueuePruneResult(TypedDict):
    root: str
    statuses: list[str]
    dry_run: bool
    keep: int | None
    older_than: str | None
    candidate_count: int
    deleted_count: int
    retained_count: int
    bytes_considered: int
    bytes_deleted: int
    candidates: list[str]
    deleted: list[str]
