from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from snowiki.compiler.taxonomy import PageType, compiled_page_path, slugify
from snowiki.config import DEFAULT_SNOWIKI_ROOT, SNOWIKI_ROOT_ENV_VAR
from snowiki.storage.zones import isoformat_utc

from .evidence import normalize_requested_paths, resolve_evidence
from .models import (
    FILEBACK_PROPOSAL_ID_PATTERN,
    FILEBACK_RECORD_TYPE,
    FILEBACK_SOURCE_TYPE,
    PROPOSAL_VERSION,
    EvidenceResolution,
    FilebackDraft,
    FilebackProposal,
    FilebackTarget,
    RawRefDict,
    coerce_raw_ref,
    require_exact_int_field,
    require_mapping,
    require_string_field,
    require_text,
    string_list,
    stringify_mapping,
)
from .payload import build_proposed_write_set


def resolve_preview_root(root: Path | None) -> Path:
    """Resolve a preview root without creating storage directories."""
    if root is not None:
        return root.expanduser().resolve()
    env_root = os.environ.get(SNOWIKI_ROOT_ENV_VAR)
    return (
        Path(env_root).expanduser().resolve()
        if env_root
        else DEFAULT_SNOWIKI_ROOT.expanduser().resolve()
    )


def build_fileback_proposal(
    root: Path,
    *,
    question: str,
    answer_markdown: str,
    summary: str,
    evidence_paths: Sequence[str],
    created_at: str | None = None,
) -> FilebackProposal:
    """Build a reviewable fileback proposal without mutating workspace state."""
    normalized_question = require_text(question, field_name="question")
    normalized_answer = require_text(answer_markdown, field_name="answer_markdown")
    normalized_summary = require_text(summary, field_name="summary")
    requested_paths = normalize_requested_paths(evidence_paths)
    if not requested_paths:
        raise ValueError("at least one --evidence-path is required")

    target = build_target(normalized_question)
    proposal_created_at = isoformat_utc(created_at)
    proposal_id = build_proposal_id(
        question=normalized_question,
        answer_markdown=normalized_answer,
        summary=normalized_summary,
        requested_paths=requested_paths,
    )
    evidence = resolve_evidence(root, requested_paths)
    proposed_write = build_proposed_write_set(
        proposal_id=proposal_id,
        created_at=proposal_created_at,
        draft={
            "question": normalized_question,
            "answer_markdown": normalized_answer,
            "summary": normalized_summary,
        },
        target=target,
        evidence=evidence,
    )

    return {
        "proposal_id": proposal_id,
        "proposal_version": PROPOSAL_VERSION,
        "created_at": proposal_created_at,
        "target": target,
        "draft": {
            "question": normalized_question,
            "answer_markdown": normalized_answer,
            "summary": normalized_summary,
        },
        "evidence": evidence,
        "derivation": {
            "kind": "derived",
            "synthesized": True,
            "source_authorship": "reviewed_fileback_proposal",
            "honesty_note": (
                "This answer is synthesized from reviewed Snowiki evidence and stored "
                "as a derived fileback record. Supporting sources are preserved as "
                "evidence, not claimed as direct raw authorship."
            ),
            "supporting_compiled_paths": evidence["resolved_paths"]["compiled"],
            "supporting_normalized_paths": evidence["resolved_paths"]["normalized"],
            "supporting_raw_paths": evidence["resolved_paths"]["raw"],
            "supporting_record_ids": evidence["supporting_record_ids"],
        },
        "apply_plan": {
            "source_type": FILEBACK_SOURCE_TYPE,
            "record_type": FILEBACK_RECORD_TYPE,
            "record_id": proposed_write["normalized_record"]["id"],
            "raw_note_path": proposed_write["raw_note_path"],
            "normalized_path": proposed_write["normalized_path"],
            "proposed_raw_note_body": proposed_write["raw_note_body"],
            "proposed_normalized_record_payload": proposed_write["normalized_record"],
            "rebuild_required": True,
        },
    }


def extract_fileback_proposal(reviewed_payload: object) -> FilebackProposal:
    """Extract a fileback proposal from a reviewed payload."""
    payload = stringify_mapping(reviewed_payload)

    if looks_like_direct_proposal(payload):
        return coerce_fileback_proposal(payload)

    if payload.get("ok") is not True:
        raise ValueError(
            "reviewed proposal payload must come from a successful preview"
        )
    if payload.get("command") != "fileback preview":
        raise ValueError(
            "reviewed proposal payload must come from the fileback preview command"
        )

    result = payload.get("result")
    if result is None:
        raise ValueError(
            "reviewed proposal payload must include a proposal or preview result envelope"
        )
    result_payload = stringify_mapping(result)
    proposal_root = result_payload.get("root")
    if not isinstance(proposal_root, str) or not proposal_root.strip():
        raise ValueError("reviewed proposal payload must include result.root")
    proposal = result_payload.get("proposal")
    if proposal is None:
        raise ValueError("reviewed proposal payload must include result.proposal")
    return coerce_fileback_proposal(stringify_mapping(proposal))


def build_target(question: str) -> FilebackTarget:
    slug = slugify(question)
    return {
        "title": question,
        "slug": slug,
        "compiled_path": compiled_page_path(PageType.QUESTION, slug),
    }


def build_proposal_id(
    *,
    question: str,
    answer_markdown: str,
    summary: str,
    requested_paths: Sequence[str],
) -> str:
    payload = {
        "answer_markdown": answer_markdown,
        "question": question,
        "requested_paths": list(requested_paths),
        "summary": summary,
        "version": PROPOSAL_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"fileback-proposal-{digest}"


def validate_proposal_root(reviewed_payload: object, root: Path) -> None:
    payload = stringify_mapping(reviewed_payload)
    if looks_like_direct_proposal(payload):
        return
    result = payload.get("result")
    if result is None:
        raise ValueError(
            "reviewed proposal payload must include the preview result envelope"
        )
    proposal_root = stringify_mapping(result).get("root")
    if not isinstance(proposal_root, str) or not proposal_root.strip():
        raise ValueError("reviewed proposal payload must include result.root")
    if proposal_root != root.as_posix():
        raise ValueError(
            f"reviewed proposal was created for {proposal_root}, but apply is running against {root.as_posix()}"
        )


def validate_proposal_schema(proposal: FilebackProposal) -> None:
    if proposal.get("proposal_version") != PROPOSAL_VERSION:
        raise ValueError(
            f"unsupported fileback proposal version: {proposal.get('proposal_version')}"
        )
    proposal_id = require_text(proposal.get("proposal_id", ""), field_name="proposal_id")
    if FILEBACK_PROPOSAL_ID_PATTERN.fullmatch(proposal_id) is None:
        raise ValueError("proposal_id must match fileback-proposal-<16 lowercase hex chars>")
    _ = require_text(proposal.get("created_at", ""), field_name="created_at")

    target = proposal["target"]
    _ = require_text(target.get("title", ""), field_name="target.title")
    _ = require_text(target.get("slug", ""), field_name="target.slug")
    _ = require_text(target.get("compiled_path", ""), field_name="target.compiled_path")

    apply_plan = proposal["apply_plan"]
    _ = require_text(str(apply_plan.get("source_type", "")), field_name="apply_plan.source_type")
    _ = require_text(str(apply_plan.get("record_type", "")), field_name="apply_plan.record_type")
    _ = require_text(str(apply_plan.get("record_id", "")), field_name="apply_plan.record_id")
    _ = require_text(
        str(apply_plan.get("normalized_path", "")),
        field_name="apply_plan.normalized_path",
    )


def coerce_fileback_proposal(value: Mapping[str, object]) -> FilebackProposal:
    return {
        "proposal_id": str(value.get("proposal_id", "")),
        "proposal_version": require_exact_int_field(value, "proposal_version"),
        "created_at": str(value.get("created_at", "")),
        "target": coerce_target(require_mapping(value, "target")),
        "draft": coerce_draft(require_mapping(value, "draft")),
        "evidence": coerce_evidence(require_mapping(value, "evidence")),
        "derivation": require_mapping(value, "derivation"),
        "apply_plan": require_mapping(value, "apply_plan"),
    }


def coerce_draft(value: Mapping[str, object]) -> FilebackDraft:
    return {
        "question": require_text(
            require_string_field(value, "question"), field_name="question"
        ),
        "answer_markdown": require_text(
            require_string_field(value, "answer_markdown"),
            field_name="answer_markdown",
        ),
        "summary": require_text(
            require_string_field(value, "summary"), field_name="summary"
        ),
    }


def coerce_evidence(value: Mapping[str, object]) -> EvidenceResolution:
    requested_paths = string_list(value.get("requested_paths"))
    if not requested_paths:
        raise ValueError("at least one evidence path is required")
    resolved_paths_mapping = require_mapping(value, "resolved_paths")
    supporting_raw_refs_value = value.get("supporting_raw_refs")
    supporting_raw_refs: list[RawRefDict] = []
    if isinstance(supporting_raw_refs_value, list):
        for raw_ref in supporting_raw_refs_value:
            if isinstance(raw_ref, Mapping):
                supporting_raw_refs.append(
                    coerce_raw_ref({str(key): item for key, item in raw_ref.items()})
                )
    return {
        "requested_paths": requested_paths,
        "resolved_paths": {
            "compiled": string_list(resolved_paths_mapping.get("compiled")),
            "normalized": string_list(resolved_paths_mapping.get("normalized")),
            "raw": string_list(resolved_paths_mapping.get("raw")),
        },
        "supporting_record_ids": string_list(value.get("supporting_record_ids")),
        "supporting_raw_refs": supporting_raw_refs,
    }


def coerce_target(value: Mapping[str, object]) -> FilebackTarget:
    return {
        "title": str(value.get("title", "")),
        "slug": str(value.get("slug", "")),
        "compiled_path": str(value.get("compiled_path", "")),
    }


def looks_like_direct_proposal(payload: Mapping[str, object]) -> bool:
    return {
        "proposal_id",
        "proposal_version",
        "created_at",
        "target",
        "draft",
        "evidence",
        "derivation",
        "apply_plan",
    }.issubset(payload)
