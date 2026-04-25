from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from snowiki.fileback.models import FilebackProposal
from snowiki.fileback.queue.codec import (
    build_queue_envelope,
    coerce_queued_fileback_proposal,
)
from snowiki.fileback.queue.lifecycle import (
    list_queued_fileback_proposals,
    queue_fileback_proposal,
    reject_queued_fileback_proposal,
    show_queued_fileback_proposal,
)
from snowiki.fileback.queue.policy import classify_low_risk_auto_apply
from snowiki.fileback.queue.prune import prune_queued_fileback_proposals
from snowiki.fileback.queue.store import (
    find_existing_queue_state_paths,
    pending_proposal_path,
)


def test_queue_fileback_proposal_writes_pending_envelope(tmp_path: Path) -> None:
    proposal = _proposal()

    result = queue_fileback_proposal(
        tmp_path,
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )

    assert result == {
        "queue_version": 1,
        "proposal_id": "fileback-proposal-0123456789abcdef",
        "queued_at": "2026-04-25T09:00:00Z",
        "status": "pending",
        "decision": "queued",
        "impact": "medium",
        "requires_human_review": True,
        "reasons": ["requires_human_review"],
        "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
    }

    payload = json.loads((tmp_path / result["proposal_path"]).read_text(encoding="utf-8"))
    assert payload == build_queue_envelope(
        tmp_path.resolve(),
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )


def test_queue_fileback_proposal_rejects_duplicate_state(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")
    _ = reject_queued_fileback_proposal(tmp_path, proposal["proposal_id"], reason="No.")

    assert find_existing_queue_state_paths(tmp_path.resolve(), proposal["proposal_id"])
    with pytest.raises(ValueError, match="already exists"):
        queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T10:00:00Z")


def test_list_queued_fileback_proposals_returns_pending_metadata(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(
        tmp_path,
        proposal,
        queued_at="2026-04-25T09:00:00Z",
    )

    assert list_queued_fileback_proposals(tmp_path) == [
        {
            "proposal_id": "fileback-proposal-0123456789abcdef",
            "queued_at": "2026-04-25T09:00:00Z",
            "status": "pending",
            "decision": "queued",
            "impact": "medium",
            "requires_human_review": True,
            "reasons": ["requires_human_review"],
            "proposal_path": "queue/proposals/pending/fileback-proposal-0123456789abcdef.json",
            "target": proposal["target"],
            "summary": "Summary",
            "evidence_requested_paths": ["compiled/summaries/source.md"],
        }
    ]


def test_pending_proposal_path_rejects_unsafe_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="proposal_id must match"):
        pending_proposal_path(tmp_path, "../evil")


def test_list_queued_fileback_proposals_filters_by_status(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    rejected = reject_queued_fileback_proposal(
        tmp_path,
        proposal["proposal_id"],
        reason="Needs better evidence.",
    )

    assert list_queued_fileback_proposals(tmp_path) == []
    assert list_queued_fileback_proposals(tmp_path, status="rejected") == [
        {
            "proposal_id": proposal["proposal_id"],
            "queued_at": "2026-04-25T09:00:00Z",
            "status": "rejected",
            "decision": "queued",
            "impact": "medium",
            "requires_human_review": False,
            "reasons": ["requires_human_review"],
            "proposal_path": rejected["proposal_path"],
            "target": proposal["target"],
            "summary": "Summary",
            "evidence_requested_paths": ["compiled/summaries/source.md"],
        }
    ]


def test_show_queued_fileback_proposal_hides_payload_by_default(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    shown = show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])
    verbose = show_queued_fileback_proposal(tmp_path, proposal["proposal_id"], verbose=True)

    assert "proposal" not in shown
    assert verbose["proposal"] == proposal


def test_show_queued_fileback_proposal_rejects_symlinked_queue_file(
    tmp_path: Path,
) -> None:
    proposal = _proposal()
    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps(build_queue_envelope(tmp_path.resolve(), proposal)),
        encoding="utf-8",
    )
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)

    with pytest.raises(ValueError, match="non-symlink regular file"):
        show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])


def test_show_queued_fileback_proposal_rejects_filename_envelope_mismatch(
    tmp_path: Path,
) -> None:
    requested = _proposal("fileback-proposal-0000000000000001")
    embedded = _proposal("fileback-proposal-0000000000000002")
    target = tmp_path / "queue" / "proposals" / "pending" / f"{requested['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(build_queue_envelope(tmp_path.resolve(), embedded)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requested proposal|queue filename"):
        show_queued_fileback_proposal(tmp_path, requested["proposal_id"])


def test_list_queued_fileback_proposals_rejects_status_mismatch(tmp_path: Path) -> None:
    proposal = _proposal()
    envelope = build_queue_envelope(tmp_path.resolve(), proposal)
    envelope["status"] = "rejected"
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ValueError, match="status does not match"):
        list_queued_fileback_proposals(tmp_path)


def test_show_queued_fileback_proposal_rejects_root_mismatch(tmp_path: Path) -> None:
    proposal = _proposal()
    envelope = build_queue_envelope(tmp_path.resolve(), proposal)
    envelope["root"] = (tmp_path / "other-root").as_posix()
    target = tmp_path / "queue" / "proposals" / "pending" / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ValueError, match="queue root"):
        show_queued_fileback_proposal(tmp_path, proposal["proposal_id"])


def test_reject_queued_fileback_proposal_moves_to_terminal_state(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")

    result = reject_queued_fileback_proposal(
        tmp_path,
        proposal["proposal_id"],
        reason="Needs stronger provenance.",
    )

    assert not pending_proposal_path(tmp_path.resolve(), proposal["proposal_id"]).exists()
    rejected_path = tmp_path / result["proposal_path"]
    assert rejected_path.exists()
    payload = coerce_queued_fileback_proposal(
        json.loads(rejected_path.read_text(encoding="utf-8"))
    )
    assert payload["status"] == "rejected"
    assert payload.get("previous_status") == "pending"
    assert payload.get("transition_reason") == "Needs stronger provenance."


def test_reject_queued_fileback_proposal_rejects_duplicate_terminal_state(tmp_path: Path) -> None:
    proposal = _proposal()
    _ = queue_fileback_proposal(tmp_path, proposal, queued_at="2026-04-25T09:00:00Z")
    _write_terminal_envelope(
        tmp_path,
        proposal,
        status="applied",
        transitioned_at="2026-04-25T10:00:00Z",
    )

    with pytest.raises(ValueError, match="must exist only as pending"):
        reject_queued_fileback_proposal(tmp_path, proposal["proposal_id"], reason="No.")


def test_prune_queued_fileback_proposals_is_dry_run_by_default(tmp_path: Path) -> None:
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000001"),
        status="applied",
        transitioned_at="2026-04-25T09:00:00Z",
    )
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000002"),
        status="applied",
        transitioned_at="2026-04-25T10:00:00Z",
    )

    result = prune_queued_fileback_proposals(tmp_path, status="applied", keep=1)

    assert result["dry_run"] is True
    assert result["candidate_count"] == 1
    assert result["deleted_count"] == 0
    assert (tmp_path / result["candidates"][0]).exists()


def test_prune_queued_fileback_proposals_uses_age_without_default_keep(tmp_path: Path) -> None:
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000001"),
        status="applied",
        transitioned_at="2020-01-01T00:00:00Z",
    )
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000002"),
        status="applied",
        transitioned_at="2020-01-02T00:00:00Z",
    )

    result = prune_queued_fileback_proposals(
        tmp_path,
        status="applied",
        older_than=timedelta(days=1),
    )

    assert result["keep"] is None
    assert result["candidate_count"] == 2


def test_prune_queued_fileback_proposals_skips_non_proposal_json(tmp_path: Path) -> None:
    terminal_dir = tmp_path / "queue" / "proposals" / "rejected"
    terminal_dir.mkdir(parents=True)
    (terminal_dir / "secrets.json").write_text('{"secret": true}', encoding="utf-8")
    (terminal_dir / "fileback-proposal-0000000000000001.json").write_text(
        "not-json",
        encoding="utf-8",
    )
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000002"),
        status="rejected",
        transitioned_at="2020-01-02T00:00:00Z",
    )

    result = prune_queued_fileback_proposals(
        tmp_path,
        status="rejected",
        older_than=timedelta(days=1),
        dry_run=False,
    )

    assert result["deleted_count"] == 1
    assert (terminal_dir / "secrets.json").exists()
    assert (terminal_dir / "fileback-proposal-0000000000000001.json").exists()


def test_prune_queued_fileback_proposals_rejects_symlinked_status_dir(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    status_parent = tmp_path / "queue" / "proposals"
    status_parent.mkdir(parents=True)
    (status_parent / "failed").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"):
        prune_queued_fileback_proposals(tmp_path, status="failed")


def test_prune_queued_fileback_proposals_deletes_when_requested(tmp_path: Path) -> None:
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000001"),
        status="failed",
        transitioned_at="2026-04-25T09:00:00Z",
    )
    _write_terminal_envelope(
        tmp_path,
        _proposal("fileback-proposal-0000000000000002"),
        status="failed",
        transitioned_at="2026-04-25T10:00:00Z",
    )

    result = prune_queued_fileback_proposals(
        tmp_path,
        status="failed",
        keep=1,
        dry_run=False,
    )

    assert result["deleted_count"] == 1
    assert not (tmp_path / result["deleted"][0]).exists()


def test_classify_low_risk_auto_apply_rejects_collisions(tmp_path: Path) -> None:
    proposal = _proposal()
    raw_path = tmp_path / proposal["apply_plan"]["raw_note_path"]
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("existing", encoding="utf-8")

    decision = classify_low_risk_auto_apply(tmp_path, proposal)

    assert decision["decision"] == "queued"
    assert decision["requires_human_review"] is True
    assert "colliding_raw_note_path" in decision["reasons"]


def test_classify_low_risk_auto_apply_allows_new_manual_question(tmp_path: Path) -> None:
    decision = classify_low_risk_auto_apply(tmp_path, _proposal())

    assert decision == {
        "decision": "auto_applied",
        "impact": "low",
        "requires_human_review": False,
        "reasons": ["runtime_low_risk_policy_passed"],
    }


def test_coerce_queued_fileback_proposal_rejects_unknown_status() -> None:
    envelope = build_queue_envelope(
        Path("/tmp/wiki"),
        _proposal(),
        queued_at="2026-04-25T09:00:00Z",
    )
    envelope["status"] = "unknown"

    with pytest.raises(ValueError, match="status must be pending, applied"):
        coerce_queued_fileback_proposal(envelope)


def _proposal(
    proposal_id: str = "fileback-proposal-0123456789abcdef",
) -> FilebackProposal:
    return {
        "proposal_id": proposal_id,
        "proposal_version": 1,
        "created_at": "2026-04-25T09:00:00Z",
        "target": {
            "title": "What did we ship?",
            "slug": "what-did-we-ship",
            "compiled_path": "compiled/questions/what-did-we-ship.md",
        },
        "draft": {
            "question": "What did we ship?",
            "answer_markdown": "Answer",
            "summary": "Summary",
        },
        "evidence": {
            "requested_paths": ["compiled/summaries/source.md"],
            "resolved_paths": {"compiled": [], "normalized": [], "raw": []},
            "supporting_record_ids": [],
            "supporting_raw_refs": [],
        },
        "derivation": {},
        "apply_plan": {
            "source_type": "manual-question",
            "record_type": "question",
            "record_id": "question-what-did-we-ship-abc123",
            "raw_note_path": "raw/manual/questions/2026/04/25/what-did-we-ship.md",
            "normalized_path": "normalized/manual-question/2026/04/25/question.json",
            "proposed_raw_note_body": "---\nsource_type: manual-question\n---\n",
            "proposed_normalized_record_payload": {"id": "question-what-did-we-ship-abc123"},
            "rebuild_required": True,
        },
    }


def _write_terminal_envelope(
    tmp_path: Path,
    proposal: FilebackProposal,
    *,
    status: str,
    transitioned_at: str,
) -> None:
    envelope = build_queue_envelope(
        tmp_path.resolve(),
        proposal,
        queued_at="2026-04-25T08:00:00Z",
    )
    envelope["status"] = status
    envelope["previous_status"] = "pending"
    envelope["transitioned_at"] = transitioned_at
    envelope["transition_reason"] = "test"
    envelope["result"] = {"ok": True}
    target = tmp_path / "queue" / "proposals" / status / f"{proposal['proposal_id']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(envelope), encoding="utf-8")
