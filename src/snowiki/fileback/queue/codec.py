from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from snowiki.storage.zones import isoformat_utc, relative_to_root

from ..models import (
    QUEUE_VERSION,
    FilebackProposal,
    QueuedFilebackProposal,
    QueuedFilebackResult,
    QueuedFilebackSummary,
    require_text,
    stringify_mapping,
)
from ..proposal import coerce_fileback_proposal, validate_proposal_schema
from .store import validate_queue_file_path, validate_queue_proposal_id
from .types import PENDING_QUEUE_STATUS, QueueStatus


def load_queued_fileback_proposal(path: Path) -> QueuedFilebackProposal:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return coerce_queued_fileback_proposal(payload)


def load_validated_queued_fileback_proposal(
    root: Path,
    path: Path,
    expected_status: QueueStatus,
    *,
    expected_proposal_id: str | None = None,
    require_root_match: bool = True,
) -> QueuedFilebackProposal:
    validate_queue_file_path(root, path, expected_status)
    envelope = load_queued_fileback_proposal(path)
    if expected_proposal_id is not None and envelope["proposal_id"] != expected_proposal_id:
        raise ValueError("queued proposal id does not match requested proposal")
    if envelope["proposal_id"] != path.stem:
        raise ValueError("queued proposal id does not match queue filename")
    if envelope["status"] != expected_status:
        raise ValueError("queued proposal status does not match queue directory")
    if require_root_match and envelope["root"] != root.as_posix():
        raise ValueError(
            f"queued proposal was created for {envelope['root']}, but queue root is {root.as_posix()}"
        )
    return envelope


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
        "proposal": proposal,
    }


def coerce_queued_fileback_proposal(value: object) -> QueuedFilebackProposal:
    payload = stringify_mapping(value)
    queue_version = payload.get("queue_version")
    if isinstance(queue_version, bool) or queue_version != QUEUE_VERSION:
        raise ValueError(f"unsupported fileback queue version: {queue_version}")
    proposal_id = str(payload.get("proposal_id", ""))
    validate_queue_proposal_id(proposal_id)
    proposal = coerce_fileback_proposal(stringify_mapping(payload.get("proposal")))
    validate_proposal_schema(proposal)
    if proposal["proposal_id"] != proposal_id:
        raise ValueError("queued proposal id does not match embedded proposal")

    envelope: dict[str, object] = {
        "queue_version": QUEUE_VERSION,
        "proposal_id": proposal_id,
        "queued_at": require_text(str(payload.get("queued_at", "")), field_name="queued_at"),
        "root": require_text(str(payload.get("root", "")), field_name="root"),
        "status": require_queue_status(payload.get("status")),
        "proposal": proposal,
    }
    return cast(QueuedFilebackProposal, cast(object, envelope))


def queue_result(
    root: Path, envelope: QueuedFilebackProposal, written_path: Path
) -> QueuedFilebackResult:
    return {
        "queue_version": envelope["queue_version"],
        "proposal_id": envelope["proposal_id"],
        "queued_at": envelope["queued_at"],
        "status": envelope["status"],
        "proposal_path": relative_to_root(root, written_path),
    }


def queue_summary(
    root: Path, envelope: QueuedFilebackProposal, path: Path
) -> QueuedFilebackSummary:
    return {
        "proposal_id": envelope["proposal_id"],
        "queued_at": envelope["queued_at"],
        "status": envelope["status"],
        "proposal_path": relative_to_root(root, path),
        "target": envelope["proposal"]["target"],
        "summary": envelope["proposal"]["draft"]["summary"],
        "evidence_requested_paths": envelope["proposal"]["evidence"]["requested_paths"],
    }


def build_fileback_preview_result(
    *,
    root: Path,
    proposal: FilebackProposal,
    queue_result: QueuedFilebackResult | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "root": root.as_posix(),
        "proposal": proposal,
        "proposed_write": {
            "raw_note_body": proposal["apply_plan"]["proposed_raw_note_body"],
            "normalized_record_payload": proposal["apply_plan"][
                "proposed_normalized_record_payload"
            ],
        },
    }
    if queue_result is not None:
        result["queue"] = queue_result
    return result


def build_queue_list_result(
    *,
    root: Path,
    proposals: list[QueuedFilebackSummary],
) -> dict[str, Any]:
    return {
        "root": root.as_posix(),
        "status": PENDING_QUEUE_STATUS,
        "proposals": proposals,
    }


def reviewed_payload_from_queue(envelope: QueuedFilebackProposal) -> dict[str, Any]:
    return {
        "ok": True,
        "command": "fileback preview",
        "result": {
            "root": envelope["root"],
            "proposal": envelope["proposal"],
        },
    }


def require_queue_status(value: object) -> QueueStatus:
    normalized = require_text(str(value or ""), field_name="status")
    if normalized == PENDING_QUEUE_STATUS:
        return PENDING_QUEUE_STATUS
    raise ValueError("status must be pending")
