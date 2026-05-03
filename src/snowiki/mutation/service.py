from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self, cast

from snowiki.config import resolve_snowiki_root
from snowiki.fileback.apply import validate_apply_plan
from snowiki.fileback.evidence import dedupe_supporting_raw_refs, resolve_evidence
from snowiki.fileback.models import FILEBACK_RECORD_TYPE, FILEBACK_SOURCE_TYPE
from snowiki.fileback.payload import build_proposed_write_set, normalized_store_payload
from snowiki.fileback.proposal import (
    build_proposal_id,
    build_target,
    extract_fileback_proposal,
    validate_proposal_root,
    validate_proposal_schema,
)
from snowiki.markdown.discovery import MarkdownSource, discover_markdown_sources
from snowiki.markdown.frontmatter import parse_markdown_document
from snowiki.markdown.ingest import build_markdown_payload
from snowiki.markdown.source_prune import SourcePruneCandidate
from snowiki.markdown.source_state import count_stale_markdown_sources
from snowiki.privacy import PrivacyGate
from snowiki.storage.provenance import RawRef
from snowiki.storage.zones import isoformat_utc

from .adapters import MutationStorage
from .domain import (
    IngestMutation,
    Mutation,
    MutationFailure,
    MutationOutcome,
    RebuildMutation,
    RebuildOutcome,
    ReviewedFilebackMutation,
    SourcePruneMutation,
)
from .finalizer import RebuildFinalizer

MUTATION_LIFECYCLE_ORDER: tuple[str, ...] = (
    "parse",
    "validate",
    "write_raw",
    "write_normalized",
    "compile",
    "clear_cache",
    "write_manifest",
)


@dataclass(frozen=True, slots=True)
class MutationService:
    """Application service that owns mutation lifecycle ordering."""

    storage: MutationStorage
    finalizer: RebuildFinalizer

    @classmethod
    def from_root(cls, root: Path) -> Self:
        return cls(
            storage=MutationStorage(root),
            finalizer=RebuildFinalizer.from_root(root),
        )

    def apply(self, mutation: Mutation) -> MutationOutcome:
        """Dispatch a mutation through the target Phase 6 lifecycle."""
        if isinstance(mutation, IngestMutation):
            return self.apply_ingest(mutation)
        if isinstance(mutation, ReviewedFilebackMutation):
            return self.apply_reviewed_fileback(mutation)
        if isinstance(mutation, SourcePruneMutation):
            return self.apply_source_prune(mutation)
        return self.apply_rebuild(mutation)

    def apply_ingest(self, mutation: IngestMutation) -> MutationOutcome:
        """Parse, validate, and persist ingest mutations through storage adapters."""
        root = mutation.root.expanduser().resolve()
        gate = PrivacyGate()
        gate.ensure_allowed_source(mutation.source_path)
        sources = discover_markdown_sources(
            mutation.source_path,
            source_root=mutation.source_root,
        )
        documents = [self._store_markdown_source(source, gate=gate) for source in sources]
        source_root = (
            sources[0].source_root.as_posix()
            if sources
            else mutation.source_path.resolve().as_posix()
        )
        rebuild = (
            self.finalizer.finalize(
                RebuildMutation(
                    root=root,
                    reason="ingest",
                    mutation_id=mutation.mutation_id,
                )
            )
            if mutation.finalize
            else None
        )
        raw_paths = tuple(str(document["raw_path"]) for document in documents)
        normalized_paths = tuple(
            str(document["normalized_path"]) for document in documents
        )
        return MutationOutcome(
            kind=mutation.kind,
            root=root,
            accepted=True,
            mutation_id=mutation.mutation_id,
            raw_paths=raw_paths,
            normalized_paths=normalized_paths,
            rebuild_required=bool(documents) and rebuild is None,
            rebuild=rebuild,
            detail={
                "root": root.as_posix(),
                "source_root": source_root,
                "documents_seen": len(documents),
                "documents_inserted": _count_documents_by_status(documents, "inserted"),
                "documents_updated": _count_documents_by_status(documents, "updated"),
                "documents_unchanged": _count_documents_by_status(documents, "unchanged"),
                "documents_stale": count_stale_markdown_sources(
                    root,
                    source_root=source_root,
                    include_untracked=False,
                ),
                "documents": documents,
            },
        )

    def apply_reviewed_fileback(
        self, mutation: ReviewedFilebackMutation
    ) -> MutationOutcome:
        """Apply reviewed fileback payloads without queue cleanup before success."""
        root = resolve_snowiki_root(mutation.root)
        proposal = extract_fileback_proposal(mutation.reviewed_payload)
        validate_proposal_root(mutation.reviewed_payload, root)
        validate_proposal_schema(proposal)

        draft = proposal["draft"]
        requested_paths = proposal["evidence"]["requested_paths"]
        expected_proposal_id = build_proposal_id(
            question=draft["question"],
            answer_markdown=draft["answer_markdown"],
            summary=draft["summary"],
            requested_paths=requested_paths,
        )
        if proposal["proposal_id"] != expected_proposal_id:
            raise ValueError("reviewed proposal id no longer matches its draft and evidence")

        target = build_target(draft["question"])
        if proposal["target"] != target:
            raise ValueError("proposal target no longer matches the reviewed question")

        evidence = resolve_evidence(root, requested_paths)
        proposed_write = build_proposed_write_set(
            proposal_id=proposal["proposal_id"],
            created_at=proposal["created_at"],
            draft=draft,
            target=target,
            evidence=evidence,
        )
        validate_apply_plan(proposal["apply_plan"], proposed_write)
        applied_at = isoformat_utc(None)

        raw_note_path = proposed_write["raw_note_path"]
        _ = self.storage.write_bytes(
            raw_note_path,
            proposed_write["raw_note_body"].encode("utf-8"),
            mtime=proposal["created_at"],
        )
        raw_ref = proposed_write["raw_ref"]
        provenance_refs: list[RawRef] = [
            raw_ref,
            *dedupe_supporting_raw_refs(evidence["supporting_raw_refs"], raw_ref["path"]),
        ]
        normalized_record = cast(Mapping[str, object], proposed_write["normalized_record"])
        store_result = self.storage.store_record(
            source_type=FILEBACK_SOURCE_TYPE,
            record_type=FILEBACK_RECORD_TYPE,
            record_id=str(normalized_record["id"]),
            payload=normalized_store_payload(normalized_record),
            raw_ref=provenance_refs,
            recorded_at=str(normalized_record["recorded_at"]),
        )
        rebuild = (
            self.finalizer.finalize(
                RebuildMutation(
                    root=root,
                    reason="reviewed_fileback",
                    mutation_id=mutation.mutation_id,
                )
            )
            if mutation.finalize
            else None
        )
        return MutationOutcome(
            kind=mutation.kind,
            root=root,
            accepted=True,
            mutation_id=mutation.mutation_id,
            raw_paths=(raw_ref["path"],),
            normalized_paths=(store_result["path"],),
            rebuild_required=rebuild is None,
            rebuild=rebuild,
            detail={
                "root": root.as_posix(),
                "applied_at": applied_at,
                "proposal_id": proposal["proposal_id"],
                "proposal_version": proposal["proposal_version"],
                "raw_ref": raw_ref,
                "supporting_raw_ref_count": len(evidence["supporting_raw_refs"]),
                "normalized_path": store_result["path"],
                "compiled_path": target["compiled_path"],
            },
        )

    def apply_source_prune(self, mutation: SourcePruneMutation) -> MutationOutcome:
        """Apply confirmed source pruning while preserving dry-run-first behavior."""
        root = mutation.root.expanduser().resolve()
        candidates = self.storage.plan_missing_source_prune()
        selected_candidates = _select_source_prune_candidates(
            candidates,
            mutation.candidate_paths,
        )
        if selected_candidates is None:
            missing = sorted(set(mutation.candidate_paths) - _candidate_path_set(candidates))
            return MutationOutcome(
                kind=mutation.kind,
                root=root,
                accepted=False,
                mutation_id=mutation.mutation_id,
                failure=MutationFailure(
                    code="unknown_source_prune_candidate",
                    message="source prune candidate path was not found",
                    phase="validate",
                    detail={"candidate_paths": missing},
                ),
                detail=_source_prune_detail(
                    root=root,
                    dry_run=mutation.dry_run,
                    candidates=candidates,
                    deleted=[],
                    tombstone_path=None,
                ),
            )
        if mutation.dry_run:
            return MutationOutcome(
                kind=mutation.kind,
                root=root,
                accepted=True,
                mutation_id=mutation.mutation_id,
                rebuild_required=bool(selected_candidates),
                detail=_source_prune_detail(
                    root=root,
                    dry_run=True,
                    candidates=selected_candidates,
                    deleted=[],
                    tombstone_path=None,
                ),
            )
        if not mutation.confirmed:
            return MutationOutcome(
                kind=mutation.kind,
                root=root,
                accepted=False,
                mutation_id=mutation.mutation_id,
                failure=MutationFailure(
                    code="source_prune_confirmation_required",
                    message="source prune deletion requires confirmation",
                    phase="validate",
                ),
                rebuild_required=bool(selected_candidates),
                detail=_source_prune_detail(
                    root=root,
                    dry_run=False,
                    candidates=selected_candidates,
                    deleted=[],
                    tombstone_path=None,
                ),
            )

        deleted = self.storage.delete_source_prune_candidates(selected_candidates)
        tombstone_path = self.storage.write_source_prune_tombstone(
            selected_candidates,
            deleted,
        )
        rebuild = (
            self.finalizer.finalize(
                RebuildMutation(
                    root=root,
                    reason="source_prune",
                    mutation_id=mutation.mutation_id,
                )
            )
            if deleted and mutation.finalize
            else None
        )
        return MutationOutcome(
            kind=mutation.kind,
            root=root,
            accepted=True,
            mutation_id=mutation.mutation_id,
            deleted_paths=tuple(deleted),
            rebuild_required=bool(deleted) and rebuild is None,
            rebuild=rebuild,
            detail=_source_prune_detail(
                root=root,
                dry_run=False,
                candidates=selected_candidates,
                deleted=deleted,
                tombstone_path=tombstone_path,
            ),
        )

    def apply_rebuild(self, mutation: RebuildMutation) -> MutationOutcome:
        """Delegate rebuild finalization to the rebuild finalizer boundary."""
        rebuild = self.finalizer.finalize(mutation)
        return MutationOutcome(
            kind=mutation.kind,
            root=mutation.root,
            accepted=True,
            mutation_id=mutation.mutation_id,
            rebuild_required=False,
            rebuild=rebuild,
            detail={"reason": mutation.reason},
        )

    def _store_markdown_source(
        self, source: MarkdownSource, *, gate: PrivacyGate
    ) -> dict[str, object]:
        gate.ensure_allowed_source(source.path)
        raw_ref = self.storage.store_raw_file("markdown", source.path)
        content = source.path.read_text(encoding="utf-8")
        parsed = parse_markdown_document(content)
        payload = build_markdown_payload(source, parsed, raw_ref)
        result = self.storage.store_markdown_document(
            source_root=source.source_root.as_posix(),
            relative_path=source.relative_path,
            payload=payload,
            raw_ref=raw_ref,
            recorded_at=str(raw_ref["mtime"]),
        )
        return {
            "relative_path": source.relative_path,
            "record_id": result["id"],
            "content_hash": str(raw_ref["sha256"]),
            "status": result["status"],
            "normalized_path": result["path"],
            "raw_path": str(raw_ref["path"]),
        }


def _count_documents_by_status(
    documents: Sequence[Mapping[str, object]], status: str
) -> int:
    return sum(1 for document in documents if document["status"] == status)


def _candidate_path_set(candidates: Sequence[SourcePruneCandidate]) -> set[str]:
    return {candidate["path"] for candidate in candidates}


def _select_source_prune_candidates(
    candidates: list[SourcePruneCandidate], candidate_paths: tuple[str, ...]
) -> list[SourcePruneCandidate] | None:
    if not candidate_paths:
        return candidates
    requested = set(candidate_paths)
    available = _candidate_path_set(candidates)
    if not requested.issubset(available):
        return None
    return [candidate for candidate in candidates if candidate["path"] in requested]


def _source_prune_detail(
    *,
    root: Path,
    dry_run: bool,
    candidates: list[SourcePruneCandidate],
    deleted: list[str],
    tombstone_path: str | None,
) -> dict[str, object]:
    return {
        "root": root.as_posix(),
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "deleted_count": len(deleted),
        "candidates": candidates,
        "deleted": deleted,
        "tombstone_path": tombstone_path,
    }


def rebuild_outcome_payload(outcome: RebuildOutcome) -> dict[str, object]:
    """Return the legacy rebuild payload shape for adapter callers."""
    return {
        "root": outcome.root.as_posix(),
        "compiled_count": len(outcome.compiled_paths),
        "compiled_paths": list(outcome.compiled_paths),
        "index_manifest": outcome.index_manifest,
        "pages_indexed": outcome.pages_indexed,
        "records_indexed": outcome.records_indexed,
        "search_documents": outcome.search_documents,
        "content_identity": dict(outcome.content_identity),
        "current_content_identity": dict(outcome.current_content_identity),
        "tokenizer_name": outcome.tokenizer_name,
    }


__all__ = ["MUTATION_LIFECYCLE_ORDER", "MutationService", "rebuild_outcome_payload"]
