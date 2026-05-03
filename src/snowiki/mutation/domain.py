from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class MutationKind(StrEnum):
    """Mutation variants accepted by the application mutation boundary."""

    INGEST = "ingest"
    REVIEWED_FILEBACK = "reviewed_fileback"
    SOURCE_PRUNE = "source_prune"
    REBUILD = "rebuild"


@dataclass(frozen=True, slots=True)
class IngestMutation:
    """Request to ingest Markdown source material into raw and normalized storage."""

    root: Path
    source_path: Path
    source_root: Path | None = None
    finalize: bool = False
    mutation_id: str | None = None
    kind: MutationKind = field(default=MutationKind.INGEST, init=False)


@dataclass(frozen=True, slots=True)
class ReviewedFilebackMutation:
    """Request to apply a reviewed fileback proposal as accepted knowledge."""

    root: Path
    reviewed_payload: object
    proposal_id: str | None = None
    queue_path: Path | None = None
    finalize: bool = True
    mutation_id: str | None = None
    kind: MutationKind = field(default=MutationKind.REVIEWED_FILEBACK, init=False)


@dataclass(frozen=True, slots=True)
class SourcePruneMutation:
    """Request to prune missing-source artifacts after explicit safety checks."""

    root: Path
    dry_run: bool = True
    confirmed: bool = False
    candidate_paths: tuple[str, ...] = ()
    finalize: bool = True
    mutation_id: str | None = None
    kind: MutationKind = field(default=MutationKind.SOURCE_PRUNE, init=False)


@dataclass(frozen=True, slots=True)
class RebuildMutation:
    """Request to rebuild derived compiled and index artifacts from normalized state."""

    root: Path
    reason: str = "operator"
    verify_freshness: bool = True
    mutation_id: str | None = None
    kind: MutationKind = field(default=MutationKind.REBUILD, init=False)


type Mutation = (
    IngestMutation | ReviewedFilebackMutation | SourcePruneMutation | RebuildMutation
)


@dataclass(frozen=True, slots=True)
class MutationFailure:
    """Machine-readable failure for a rejected or failed mutation."""

    code: str
    message: str
    phase: str
    detail: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class RebuildOutcome:
    """Result of rebuild finalization after manifest-last integrity checks."""

    root: Path
    compiled_paths: tuple[str, ...]
    index_manifest: str
    pages_indexed: int
    records_indexed: int
    search_documents: int
    content_identity: Mapping[str, object]
    current_content_identity: Mapping[str, object]
    tokenizer_name: str


@dataclass(frozen=True, slots=True)
class MutationOutcome:
    """Result model returned by the mutation application service."""

    kind: MutationKind
    root: Path
    accepted: bool
    mutation_id: str | None = None
    raw_paths: tuple[str, ...] = ()
    normalized_paths: tuple[str, ...] = ()
    deleted_paths: tuple[str, ...] = ()
    rebuild_required: bool = False
    rebuild: RebuildOutcome | None = None
    failure: MutationFailure | None = None
    detail: Mapping[str, object] | None = None


__all__ = [
    "IngestMutation",
    "Mutation",
    "MutationFailure",
    "MutationKind",
    "MutationOutcome",
    "RebuildMutation",
    "RebuildOutcome",
    "ReviewedFilebackMutation",
    "SourcePruneMutation",
]
