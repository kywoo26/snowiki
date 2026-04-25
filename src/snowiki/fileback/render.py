from __future__ import annotations

import hashlib
import json

from snowiki.storage.zones import ensure_utc_datetime, isoformat_utc

from .models import (
    EvidenceResolution,
    FilebackDraft,
    FilebackTarget,
    RawRefDict,
)


def build_manual_question_raw_path(
    *, slug: str, proposal_id: str, recorded_at: str
) -> str:
    moment = ensure_utc_datetime(recorded_at)
    proposal_suffix = proposal_id.removeprefix("fileback-proposal-")
    return (
        f"raw/manual/questions/{moment.year:04d}/{moment.month:02d}/"
        f"{moment.day:02d}/{slug}--{proposal_suffix}.md"
    )


def build_manual_question_note_body(
    *,
    proposal_id: str,
    created_at: str,
    draft: FilebackDraft,
    target: FilebackTarget,
    evidence: EvidenceResolution,
) -> str:
    evidence_lines = [
        f"- {path}"
        for path in [
            *evidence["resolved_paths"]["compiled"],
            *evidence["resolved_paths"]["normalized"],
            *evidence["resolved_paths"]["raw"],
        ]
    ]
    return "\n".join(
        [
            "---",
            f"title: {json.dumps(draft['question'], ensure_ascii=False)}",
            'type: "manual-question"',
            f"proposal_id: {json.dumps(proposal_id)}",
            f"created_at: {json.dumps(created_at)}",
            f"compiled_path: {json.dumps(target['compiled_path'])}",
            "---",
            f"# {draft['question']}",
            "",
            "## Summary",
            "",
            draft["summary"],
            "",
            "## Answer",
            "",
            draft["answer_markdown"],
            "",
            "## Evidence",
            "",
            *(evidence_lines or ["- _No supporting paths recorded._"]),
        ]
    )


def build_raw_ref_for_note(
    *, relative_path: str, content: str, mtime: str
) -> RawRefDict:
    rendered = content.encode("utf-8")
    return {
        "sha256": hashlib.sha256(rendered).hexdigest(),
        "path": relative_path,
        "size": len(rendered),
        "mtime": isoformat_utc(mtime),
    }
