from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class SourcePrivacyGate(Protocol):
    """Source-path privacy boundary for ingest mutations."""

    def ensure_allowed_source(self, source_path: str | Path) -> None:
        """Raise when a source path must not be ingested."""


class OperationKind(StrEnum):
    """Operation variants accepted by the application mutation boundary."""

    INGEST = "ingest"
    REVIEWED_FILEBACK = "reviewed_fileback"
    SOURCE_PRUNE = "source_prune"
    REBUILD = "rebuild"


@dataclass(frozen=True, slots=True)
class IngestOperation:
    """Request to ingest Markdown source material into raw and normalized storage."""

    root: Path
    source_path: Path
    source_root: Path | None = None
    materialize: bool = False
    source_privacy_gate: SourcePrivacyGate | None = None
    operation_id: str | None = None
    kind: OperationKind = field(default=OperationKind.INGEST, init=False)


@dataclass(frozen=True, slots=True)
class ReviewedFilebackOperation:
    """Request to apply a reviewed fileback proposal as accepted knowledge."""

    root: Path
    reviewed_payload: object
    proposal_id: str | None = None
    queue_path: Path | None = None
    materialize: bool = True
    operation_id: str | None = None
    kind: OperationKind = field(default=OperationKind.REVIEWED_FILEBACK, init=False)


@dataclass(frozen=True, slots=True)
class SourcePruneOperation:
    """Request to prune missing-source artifacts after explicit safety checks."""

    root: Path
    dry_run: bool = True
    confirmed: bool = False
    candidate_paths: tuple[str, ...] = ()
    materialize: bool = True
    operation_id: str | None = None
    kind: OperationKind = field(default=OperationKind.SOURCE_PRUNE, init=False)


@dataclass(frozen=True, slots=True)
class RebuildOperation:
    """Request to rebuild derived compiled and index artifacts from normalized state."""

    root: Path
    reason: str = "operator"
    verify_freshness: bool = True
    operation_id: str | None = None
    kind: OperationKind = field(default=OperationKind.REBUILD, init=False)


type Operation = (
    IngestOperation | ReviewedFilebackOperation | SourcePruneOperation | RebuildOperation
)


@dataclass(frozen=True, slots=True)
class OperationFailure:
    """Machine-readable failure for a rejected or failed mutation."""

    code: str
    message: str
    phase: str
    detail: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class MaterializationOutcome:
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
class OperationOutcome:
    """Result model returned by the mutation application service."""

    kind: OperationKind
    root: Path
    accepted: bool
    operation_id: str | None = None
    raw_paths: tuple[str, ...] = ()
    normalized_paths: tuple[str, ...] = ()
    deleted_paths: tuple[str, ...] = ()
    rebuild_required: bool = False
    rebuild: MaterializationOutcome | None = None
    failure: OperationFailure | None = None
    detail: Mapping[str, object] | None = None


__all__ = [
    "IngestOperation",
    "Operation",
    "OperationFailure",
    "OperationKind",
    "OperationOutcome",
    "RebuildOperation",
    "MaterializationOutcome",
    "ReviewedFilebackOperation",
    "SourcePruneOperation",
]
