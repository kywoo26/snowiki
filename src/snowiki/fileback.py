from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from snowiki.compiler.taxonomy import PageType, compiled_page_path, slugify
from snowiki.config import (
    DEFAULT_SNOWIKI_ROOT,
    SNOWIKI_ROOT_ENV_VAR,
    resolve_snowiki_root,
)
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.raw import RawStorage
from snowiki.storage.zones import (
    ensure_utc_datetime,
    isoformat_utc,
    relative_to_root,
    sanitize_segment,
)

PROPOSAL_VERSION = 1
FILEBACK_SOURCE_TYPE = "fileback"
FILEBACK_RECORD_TYPE = "fileback"


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


class LoadedNormalizedRecord(TypedDict):
    id: str
    path: str
    raw_refs: list[RawRefDict]


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
    normalized_question = _require_text(question, field_name="question")
    normalized_answer = _require_text(answer_markdown, field_name="answer_markdown")
    normalized_summary = _require_text(summary, field_name="summary")
    requested_paths = _normalize_requested_paths(evidence_paths)
    if not requested_paths:
        raise ValueError("at least one --evidence-path is required")

    target = _build_target(normalized_question)
    proposal_created_at = isoformat_utc(created_at)
    proposal_id = _build_proposal_id(
        question=normalized_question,
        answer_markdown=normalized_answer,
        summary=normalized_summary,
        requested_paths=requested_paths,
    )
    evidence = resolve_evidence(root, requested_paths)
    record_id = build_fileback_record_id(target["slug"], proposal_id)
    normalized_path = build_fileback_normalized_path(
        record_id, recorded_at=proposal_created_at
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
            "record_id": record_id,
            "normalized_path": normalized_path,
            "rebuild_required": True,
        },
    }


def apply_fileback_proposal(root: Path, reviewed_payload: object) -> dict[str, Any]:
    """Persist a reviewed fileback proposal and rebuild compiled output."""
    resolved_root = resolve_snowiki_root(root)
    proposal = extract_fileback_proposal(reviewed_payload)
    _validate_proposal_root(reviewed_payload, resolved_root)
    _validate_proposal_schema(proposal)

    draft = proposal["draft"]
    target = _build_target(draft["question"])
    if proposal["target"] != target:
        raise ValueError("proposal target no longer matches the reviewed question")

    requested_paths = proposal["evidence"]["requested_paths"]
    evidence = resolve_evidence(resolved_root, requested_paths)
    applied_at = isoformat_utc(None)
    record_id = build_fileback_record_id(target["slug"], proposal["proposal_id"])

    raw_storage = RawStorage(resolved_root)
    raw_payload = {
        "applied_at": applied_at,
        "proposal": proposal,
    }
    raw_ref = _coerce_raw_ref(
        raw_storage.store_bytes(
            FILEBACK_SOURCE_TYPE,
            json.dumps(
                raw_payload, indent=2, sort_keys=True, ensure_ascii=False
            ).encode("utf-8"),
        )
    )

    normalized_storage = NormalizedStorage(resolved_root)
    provenance_refs = [
        raw_ref,
        *_dedupe_supporting_raw_refs(evidence["supporting_raw_refs"]),
    ]
    store_result = normalized_storage.store_record(
        source_type=FILEBACK_SOURCE_TYPE,
        record_type=FILEBACK_RECORD_TYPE,
        record_id=record_id,
        payload={
            "question": draft["question"],
            "title": draft["question"],
            "summary": draft["summary"],
            "answer_markdown": draft["answer_markdown"],
            "supporting_paths": [
                *evidence["resolved_paths"]["compiled"],
                *evidence["resolved_paths"]["normalized"],
                *evidence["resolved_paths"]["raw"],
            ],
            "derivation": {
                **proposal["derivation"],
                "kind": "derived",
                "synthesized": True,
                "review_status": "applied",
                "reviewed_proposal_id": proposal["proposal_id"],
                "reviewed_proposal_version": proposal["proposal_version"],
                "applied_at": applied_at,
                "supporting_compiled_paths": evidence["resolved_paths"]["compiled"],
                "supporting_normalized_paths": evidence["resolved_paths"]["normalized"],
                "supporting_raw_paths": evidence["resolved_paths"]["raw"],
                "supporting_record_ids": evidence["supporting_record_ids"],
            },
            "compiler": {
                "summary": draft["summary"],
                "questions": [
                    {
                        "title": draft["question"],
                        "summary": draft["summary"],
                        "tags": ["fileback"],
                    }
                ],
            },
        },
        raw_ref=provenance_refs,
        recorded_at=applied_at,
    )
    rebuild_result = run_rebuild_with_integrity(resolved_root)
    return {
        "root": resolved_root.as_posix(),
        "proposal_id": proposal["proposal_id"],
        "proposal_version": proposal["proposal_version"],
        "raw_ref": raw_ref,
        "supporting_raw_ref_count": len(evidence["supporting_raw_refs"]),
        "normalized_path": store_result["path"],
        "compiled_path": target["compiled_path"],
        "rebuild": rebuild_result,
    }


def extract_fileback_proposal(reviewed_payload: object) -> FilebackProposal:
    """Extract a fileback proposal from a reviewed payload."""
    payload = _stringify_mapping(reviewed_payload)

    if _looks_like_direct_proposal(payload):
        return _coerce_fileback_proposal(payload)

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
    result_payload = _stringify_mapping(result)
    proposal_root = result_payload.get("root")
    if not isinstance(proposal_root, str) or not proposal_root.strip():
        raise ValueError("reviewed proposal payload must include result.root")
    proposal = result_payload.get("proposal")
    if proposal is None:
        raise ValueError("reviewed proposal payload must include result.proposal")
    return _coerce_fileback_proposal(_stringify_mapping(proposal))


def resolve_evidence(root: Path, requested_paths: Sequence[str]) -> EvidenceResolution:
    """Resolve supporting evidence paths into normalized and raw provenance."""
    normalized_records = _load_normalized_records(root)
    normalized_by_id = {record["id"]: record for record in normalized_records}
    resolved_compiled: list[str] = []
    resolved_normalized: list[str] = []
    resolved_raw: list[str] = []
    supporting_record_ids: list[str] = []
    supporting_raw_refs: list[RawRefDict] = []

    for requested in requested_paths:
        candidate = _resolve_workspace_path(root, requested)
        relative_path = relative_to_root(root, candidate)
        top_level = (
            candidate.parts[len(root.parts)]
            if len(candidate.parts) > len(root.parts)
            else ""
        )
        if top_level == "compiled":
            resolved_compiled.append(relative_path)
            record_ids = _compiled_record_ids(candidate)
            for record_id in record_ids:
                record = normalized_by_id.get(record_id)
                if record is None:
                    continue
                supporting_record_ids.append(record_id)
                resolved_normalized.append(record["path"])
                supporting_raw_refs.extend(record["raw_refs"])
            continue
        if top_level == "normalized":
            record = _normalized_record_for_path(normalized_records, relative_path)
            resolved_normalized.append(relative_path)
            supporting_record_ids.append(record["id"])
            supporting_raw_refs.extend(record["raw_refs"])
            continue
        if top_level == "raw":
            resolved_raw.append(relative_path)
            supporting_raw_refs.append(build_workspace_raw_ref(root, candidate))
            continue
        raise ValueError(
            f"unsupported evidence path '{requested}'; expected a raw/, normalized/, or compiled/ workspace path"
        )

    return {
        "requested_paths": list(requested_paths),
        "resolved_paths": {
            "compiled": sorted(set(resolved_compiled)),
            "normalized": sorted(set(resolved_normalized)),
            "raw": sorted(set(resolved_raw)),
        },
        "supporting_record_ids": sorted(set(supporting_record_ids)),
        "supporting_raw_refs": dedupe_raw_refs(supporting_raw_refs),
    }


def build_fileback_record_id(slug: str, proposal_id: str) -> str:
    """Build a deterministic normalized record identifier for a fileback."""
    digest = hashlib.sha256(f"{slug}:{proposal_id}".encode()).hexdigest()[:12]
    return f"fileback-{slug}-{digest}"


def build_fileback_normalized_path(record_id: str, *, recorded_at: str) -> str:
    """Return the normalized path that apply will write."""
    moment = ensure_utc_datetime(recorded_at)
    safe_source_type = sanitize_segment(FILEBACK_SOURCE_TYPE)
    return (
        f"normalized/{safe_source_type}/{moment.year:04d}/{moment.month:02d}/"
        f"{moment.day:02d}/{record_id}.json"
    )


def build_workspace_raw_ref(root: Path, path: Path) -> RawRefDict:
    """Build a raw-ref-style payload for an existing workspace artifact."""
    stat = path.stat()
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "path": relative_to_root(root, path),
        "size": stat.st_size,
        "mtime": isoformat_utc(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
    }


def dedupe_raw_refs(raw_refs: Sequence[Mapping[str, object]]) -> list[RawRefDict]:
    """Deduplicate raw refs using the compiler provenance key."""
    deduped: list[RawRefDict] = []
    seen: set[tuple[str, str]] = set()
    for raw_ref in raw_refs:
        entry = _coerce_raw_ref({str(key): value for key, value in raw_ref.items()})
        key = (entry["sha256"], entry["path"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    deduped.sort(key=lambda entry: (entry["path"], entry["sha256"]))
    return deduped


def _dedupe_supporting_raw_refs(
    raw_refs: Sequence[Mapping[str, object]],
) -> list[RawRefDict]:
    return [
        raw_ref
        for raw_ref in dedupe_raw_refs(raw_refs)
        if raw_ref["path"] != "" and not raw_ref["path"].startswith("raw/fileback/")
    ]


def _build_target(question: str) -> FilebackTarget:
    slug = slugify(question)
    return {
        "title": question,
        "slug": slug,
        "compiled_path": compiled_page_path(PageType.QUESTION, slug),
    }


def _build_proposal_id(
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


def _compiled_record_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return []
    record_ids: list[str] = []
    in_record_ids = False
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("record_ids:"):
            in_record_ids = True
            continue
        if not in_record_ids:
            continue
        if line.startswith("  - "):
            item = line[4:].strip()
            if item:
                record_ids.append(_parse_list_scalar(item))
            continue
        if line and not line[0].isspace():
            in_record_ids = False
    return sorted(set(record_ids))


def _load_normalized_records(root: Path) -> list[LoadedNormalizedRecord]:
    records: list[LoadedNormalizedRecord] = []
    normalized_root = root / "normalized"
    if not normalized_root.exists():
        return records
    for path in sorted(
        normalized_root.rglob("*.json"), key=lambda item: item.as_posix()
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        records.append(
            {
                "id": str(payload.get("id", path.stem)),
                "path": relative_to_root(root, path),
                "raw_refs": _query_raw_sources(payload),
            }
        )
    return records


def _normalize_requested_paths(evidence_paths: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for path in evidence_paths:
        stripped = str(path).strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _normalized_record_for_path(
    normalized_records: Sequence[LoadedNormalizedRecord], relative_path: str
) -> LoadedNormalizedRecord:
    for record in normalized_records:
        if record["path"] == relative_path:
            return record
    raise ValueError(f"normalized evidence path '{relative_path}' was not found")


def _parse_list_scalar(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith(('"', "'")):
        try:
            return str(json.loads(stripped))
        except json.JSONDecodeError:
            return stripped.strip("\"'")
    return stripped


def _query_raw_sources(record: Mapping[str, object]) -> list[RawRefDict]:
    refs: list[RawRefDict] = []
    raw_ref_value = record.get("raw_ref")
    if isinstance(raw_ref_value, Mapping):
        raw_ref_mapping = _stringify_mapping(raw_ref_value)
        if _is_raw_ref_mapping(raw_ref_mapping):
            refs.append(_coerce_raw_ref(raw_ref_mapping))

    provenance = record.get("provenance")
    if isinstance(provenance, Mapping):
        raw_refs = _stringify_mapping(provenance).get("raw_refs")
        if isinstance(raw_refs, list):
            for raw_ref in raw_refs:
                if isinstance(raw_ref, Mapping):
                    raw_ref_mapping = _stringify_mapping(raw_ref)
                    if _is_raw_ref_mapping(raw_ref_mapping):
                        refs.append(_coerce_raw_ref(raw_ref_mapping))
    return dedupe_raw_refs(refs)


def _is_raw_ref_mapping(value: Mapping[str, object]) -> bool:
    return {"sha256", "path", "size", "mtime"}.issubset(value)


def _require_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _resolve_workspace_path(root: Path, requested_path: str) -> Path:
    candidate = Path(requested_path).expanduser()
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    )
    try:
        _ = relative_to_root(root, resolved)
    except ValueError as exc:
        raise ValueError(
            f"evidence path '{requested_path}' must stay inside {root}"
        ) from exc
    if not resolved.exists():
        raise ValueError(f"evidence path '{requested_path}' does not exist")
    if not resolved.is_file():
        raise ValueError(f"evidence path '{requested_path}' must be a file")
    return resolved


def _validate_proposal_root(reviewed_payload: object, root: Path) -> None:
    payload = _stringify_mapping(reviewed_payload)
    if _looks_like_direct_proposal(payload):
        return
    result = payload.get("result")
    if result is None:
        raise ValueError(
            "reviewed proposal payload must include the preview result envelope"
        )
    proposal_root = _stringify_mapping(result).get("root")
    if not isinstance(proposal_root, str) or not proposal_root.strip():
        raise ValueError("reviewed proposal payload must include result.root")
    if proposal_root != root.as_posix():
        raise ValueError(
            f"reviewed proposal was created for {proposal_root}, but apply is running against {root.as_posix()}"
        )


def _validate_proposal_schema(proposal: FilebackProposal) -> None:
    if proposal.get("proposal_version") != PROPOSAL_VERSION:
        raise ValueError(
            f"unsupported fileback proposal version: {proposal.get('proposal_version')}"
        )
    _require_text(proposal.get("proposal_id", ""), field_name="proposal_id")
    _require_text(proposal.get("created_at", ""), field_name="created_at")

    target = proposal["target"]
    _require_text(target.get("title", ""), field_name="target.title")
    _require_text(target.get("slug", ""), field_name="target.slug")
    _require_text(target.get("compiled_path", ""), field_name="target.compiled_path")

    apply_plan = proposal["apply_plan"]
    _require_text(
        str(apply_plan.get("source_type", "")), field_name="apply_plan.source_type"
    )
    _require_text(
        str(apply_plan.get("record_type", "")), field_name="apply_plan.record_type"
    )
    _require_text(
        str(apply_plan.get("record_id", "")), field_name="apply_plan.record_id"
    )
    _require_text(
        str(apply_plan.get("normalized_path", "")),
        field_name="apply_plan.normalized_path",
    )


def _coerce_fileback_proposal(value: Mapping[str, object]) -> FilebackProposal:
    return {
        "proposal_id": str(value.get("proposal_id", "")),
        "proposal_version": _require_exact_int_field(value, "proposal_version"),
        "created_at": str(value.get("created_at", "")),
        "target": _coerce_target(_require_mapping(value, "target")),
        "draft": _coerce_draft(_require_mapping(value, "draft")),
        "evidence": _coerce_evidence(_require_mapping(value, "evidence")),
        "derivation": _require_dict(value, "derivation"),
        "apply_plan": _require_dict(value, "apply_plan"),
    }


def _coerce_raw_ref(value: Mapping[str, object]) -> RawRefDict:
    return {
        "sha256": str(value["sha256"]),
        "path": str(value["path"]),
        "size": _coerce_int_like_value(value["size"]),
        "mtime": str(value["mtime"]),
    }


def _coerce_draft(value: Mapping[str, object]) -> FilebackDraft:
    return {
        "question": _require_text(
            _require_string_field(value, "question"), field_name="question"
        ),
        "answer_markdown": _require_text(
            _require_string_field(value, "answer_markdown"),
            field_name="answer_markdown",
        ),
        "summary": _require_text(
            _require_string_field(value, "summary"), field_name="summary"
        ),
    }


def _coerce_evidence(value: Mapping[str, object]) -> EvidenceResolution:
    requested_paths = _string_list(value.get("requested_paths"))
    if not requested_paths:
        raise ValueError("at least one evidence path is required")
    resolved_paths_mapping = _require_mapping(value, "resolved_paths")
    supporting_raw_refs_value = value.get("supporting_raw_refs")
    supporting_raw_refs: list[RawRefDict] = []
    if isinstance(supporting_raw_refs_value, list):
        for raw_ref in supporting_raw_refs_value:
            if isinstance(raw_ref, Mapping):
                supporting_raw_refs.append(
                    _coerce_raw_ref({str(key): item for key, item in raw_ref.items()})
                )
    return {
        "requested_paths": requested_paths,
        "resolved_paths": {
            "compiled": _string_list(resolved_paths_mapping.get("compiled")),
            "normalized": _string_list(resolved_paths_mapping.get("normalized")),
            "raw": _string_list(resolved_paths_mapping.get("raw")),
        },
        "supporting_record_ids": _string_list(value.get("supporting_record_ids")),
        "supporting_raw_refs": supporting_raw_refs,
    }


def _coerce_target(value: Mapping[str, object]) -> FilebackTarget:
    return {
        "title": str(value.get("title", "")),
        "slug": str(value.get("slug", "")),
        "compiled_path": str(value.get("compiled_path", "")),
    }


def _coerce_int_like_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"expected integer-compatible value, got {type(value).__name__}")


def _looks_like_direct_proposal(payload: Mapping[str, object]) -> bool:
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


def _require_exact_int_field(value: Mapping[str, object], field_name: str) -> int:
    field_value = value.get(field_name)
    if isinstance(field_value, bool) or not isinstance(field_value, int):
        raise ValueError(f"{field_name} must be an integer")
    return field_value


def _require_dict(value: Mapping[str, object], field_name: str) -> dict[str, Any]:
    field_value = value.get(field_name)
    if not isinstance(field_value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return {str(key): item for key, item in field_value.items()}


def _require_mapping(value: Mapping[str, object], field_name: str) -> dict[str, object]:
    field_value = value.get(field_name)
    if not isinstance(field_value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return {str(key): item for key, item in field_value.items()}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _require_string_field(value: Mapping[str, object], field_name: str) -> str:
    field_value = value.get(field_name)
    if not isinstance(field_value, str):
        raise ValueError(f"{field_name} is required")
    return field_value


def _stringify_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("expected a mapping")
    return {str(key): item for key, item in value.items()}
