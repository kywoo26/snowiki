from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from snowiki.compiler.projection import make_compiler_projection
from snowiki.storage.zones import ensure_utc_datetime, sanitize_segment

from .evidence import dedupe_supporting_raw_refs
from .models import (
    FILEBACK_RECORD_TYPE,
    FILEBACK_SOURCE_TYPE,
    PROPOSAL_VERSION,
    EvidenceResolution,
    FilebackDraft,
    FilebackTarget,
    ProposedWriteSet,
    RawRefDict,
)
from .render import (
    build_manual_question_note_body,
    build_manual_question_raw_path,
    build_raw_ref_for_note,
)


def build_fileback_record_id(slug: str, proposal_id: str) -> str:
    """Build a deterministic normalized record identifier for a fileback."""
    digest = hashlib.sha256(f"{slug}:{proposal_id}".encode()).hexdigest()[:12]
    return f"question-{slug}-{digest}"


def build_fileback_normalized_path(record_id: str, *, recorded_at: str) -> str:
    """Return the normalized path that apply will write."""
    moment = ensure_utc_datetime(recorded_at)
    safe_source_type = sanitize_segment(FILEBACK_SOURCE_TYPE)
    return (
        f"normalized/{safe_source_type}/{moment.year:04d}/{moment.month:02d}/"
        f"{moment.day:02d}/{record_id}.json"
    )


def build_proposed_write_set(
    *,
    proposal_id: str,
    created_at: str,
    draft: FilebackDraft,
    target: FilebackTarget,
    evidence: EvidenceResolution,
) -> ProposedWriteSet:
    record_id = build_fileback_record_id(target["slug"], proposal_id)
    raw_note_path = build_manual_question_raw_path(
        slug=target["slug"], proposal_id=proposal_id, recorded_at=created_at
    )
    raw_note_body = build_manual_question_note_body(
        proposal_id=proposal_id,
        created_at=created_at,
        draft=draft,
        target=target,
        evidence=evidence,
    )
    raw_ref = build_raw_ref_for_note(
        relative_path=raw_note_path,
        content=raw_note_body,
        mtime=created_at,
    )
    normalized_record = build_normalized_record_payload(
        proposal_id=proposal_id,
        created_at=created_at,
        draft=draft,
        target=target,
        evidence=evidence,
        raw_ref=raw_ref,
        record_id=record_id,
    )
    return {
        "raw_note_body": raw_note_body,
        "raw_note_path": raw_note_path,
        "raw_ref": raw_ref,
        "normalized_record": normalized_record,
        "normalized_path": build_fileback_normalized_path(
            record_id, recorded_at=created_at
        ),
    }


def build_normalized_record_payload(
    *,
    proposal_id: str,
    created_at: str,
    draft: FilebackDraft,
    target: FilebackTarget,
    evidence: EvidenceResolution,
    raw_ref: RawRefDict,
    record_id: str,
) -> dict[str, Any]:
    supporting_paths = [
        *evidence["resolved_paths"]["compiled"],
        *evidence["resolved_paths"]["normalized"],
        *evidence["resolved_paths"]["raw"],
    ]
    supporting_raw_refs = [
        raw_ref,
        *dedupe_supporting_raw_refs(evidence["supporting_raw_refs"], raw_ref["path"]),
    ]
    projection = make_compiler_projection(
        title=draft["question"],
        summary=draft["summary"],
        body=draft["answer_markdown"],
        tags=["manual-question", "fileback"],
        source_identity={"content_hash": raw_ref["sha256"]},
        sections=[
            {"title": "Answer", "body": draft["answer_markdown"]},
            {"title": "Evidence", "body": "\n".join(supporting_paths)},
        ],
        taxonomy={
            "questions": [
                {
                    "title": draft["question"],
                    "summary": draft["summary"],
                    "tags": ["manual-question", "fileback"],
                }
            ],
        },
    )
    return {
        "id": record_id,
        "record_type": FILEBACK_RECORD_TYPE,
        "recorded_at": created_at,
        "source_type": FILEBACK_SOURCE_TYPE,
        "question": draft["question"],
        "title": draft["question"],
        "summary": draft["summary"],
        "answer_markdown": draft["answer_markdown"],
        "supporting_paths": supporting_paths,
        "projection": projection,
        "derivation": {
            "kind": "derived",
            "synthesized": True,
            "source_authorship": "reviewed_fileback_proposal",
            "honesty_note": (
                "This answer is synthesized from reviewed Snowiki evidence and stored "
                "as a derived manual question record. Supporting sources are preserved "
                "as evidence, not claimed as direct raw authorship."
            ),
            "reviewed_proposal_id": proposal_id,
            "reviewed_proposal_version": PROPOSAL_VERSION,
            "supporting_compiled_paths": evidence["resolved_paths"]["compiled"],
            "supporting_normalized_paths": evidence["resolved_paths"]["normalized"],
            "supporting_raw_paths": evidence["resolved_paths"]["raw"],
            "supporting_record_ids": evidence["supporting_record_ids"],
        },
        "raw_ref": raw_ref,
        "provenance": {
            "raw_refs": supporting_raw_refs,
            "link_chain": ["normalized", "raw"],
        },
        "target": target,
    }


def normalized_store_payload(record: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in record.items()
        if key
        not in {
            "id",
            "record_type",
            "recorded_at",
            "source_type",
            "raw_ref",
            "provenance",
        }
    }
