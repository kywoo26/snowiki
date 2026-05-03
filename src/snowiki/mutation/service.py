from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from .adapters import MutationStorage
from .domain import (
    IngestMutation,
    Mutation,
    MutationOutcome,
    RebuildMutation,
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
        _ = mutation
        raise NotImplementedError("Phase 6 ingest mutation skeleton only")

    def apply_reviewed_fileback(
        self, mutation: ReviewedFilebackMutation
    ) -> MutationOutcome:
        """Apply reviewed fileback payloads without queue cleanup before success."""
        _ = mutation
        raise NotImplementedError("Phase 6 reviewed fileback mutation skeleton only")

    def apply_source_prune(self, mutation: SourcePruneMutation) -> MutationOutcome:
        """Apply confirmed source pruning while preserving dry-run-first behavior."""
        _ = mutation
        raise NotImplementedError("Phase 6 source prune mutation skeleton only")

    def apply_rebuild(self, mutation: RebuildMutation) -> MutationOutcome:
        """Delegate rebuild finalization to the rebuild finalizer boundary."""
        _ = mutation
        raise NotImplementedError("Phase 6 rebuild mutation skeleton only")


__all__ = ["MUTATION_LIFECYCLE_ORDER", "MutationService"]
