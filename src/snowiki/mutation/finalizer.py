from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from snowiki.storage.index_manifest import IndexManifest, write_index_manifest

from .adapters import CompiledPageAdapter, IndexManifestAdapter, RetrievalAdapter
from .domain import RebuildMutation, RebuildOutcome

REBUILD_FINALIZATION_ORDER: tuple[str, ...] = (
    "compile_pages",
    "clear_query_cache",
    "build_retrieval_snapshot",
    "compare_content_identity",
    "write_index_manifest",
)


class RebuildFinalizationFreshnessError(RuntimeError):
    """Raised when content identity changes before manifest persistence."""

    def __init__(self, outcome: RebuildOutcome) -> None:
        super().__init__(
            "rebuild snapshot freshness changed before manifest finalization"
        )
        self.outcome: RebuildOutcome = outcome


@dataclass(frozen=True, slots=True)
class RebuildFinalizer:
    """Own rebuild finalization after mutation writes are complete."""

    compiled_pages: CompiledPageAdapter
    retrieval: RetrievalAdapter
    manifest: IndexManifestAdapter

    @classmethod
    def from_root(cls, root: Path) -> Self:
        return cls(
            compiled_pages=CompiledPageAdapter(root),
            retrieval=RetrievalAdapter(root),
            manifest=IndexManifestAdapter(root),
        )

    def finalize(self, mutation: RebuildMutation) -> RebuildOutcome:
        """Finalize compiled and index state for a rebuild mutation.

        Target order is defined by ``REBUILD_FINALIZATION_ORDER``. The manifest
        write is intentionally last so failed cache, snapshot, or identity checks
        cannot bless stale compiled/index state.
        """
        compiled_paths = self.compiled_pages.rebuild_compiled_pages()
        self.retrieval.clear_query_cache()

        tokenizer_name = self.manifest.current_tokenizer_name()
        retrieval_identity = self.manifest.retrieval_identity(tokenizer_name)
        search_document_format, lexical_index_format = self.manifest.current_index_formats()
        snapshot_identity = self.manifest.current_identity(
            retrieval_identity,
            search_document_format=search_document_format,
            lexical_index_format=lexical_index_format,
        )

        snapshot = self.retrieval.build_snapshot()
        current_identity = self.manifest.current_identity(
            retrieval_identity,
            search_document_format=search_document_format,
            lexical_index_format=lexical_index_format,
        )
        manifest = IndexManifest(
            schema_version=1,
            records_indexed=snapshot.records_indexed,
            pages_indexed=snapshot.pages_indexed,
            search_documents=snapshot.index.size,
            compiled_paths=compiled_paths,
            identity=snapshot_identity,
        )
        outcome = RebuildOutcome(
            root=mutation.root,
            compiled_paths=compiled_paths,
            index_manifest=self.manifest.manifest_relative_path(),
            pages_indexed=snapshot.pages_indexed,
            records_indexed=snapshot.records_indexed,
            search_documents=snapshot.index.size,
            content_identity=self.manifest.status_identity_payload(snapshot_identity),
            current_content_identity=self.manifest.status_identity_payload(current_identity),
            tokenizer_name=tokenizer_name,
        )
        if snapshot_identity != current_identity:
            raise RebuildFinalizationFreshnessError(outcome)
        self.write_manifest_last(manifest)
        return outcome

    def write_manifest_last(self, manifest: IndexManifest) -> None:
        """Persist the index manifest as the final rebuild step."""
        write_index_manifest(self.manifest.paths, manifest)


__all__ = [
    "REBUILD_FINALIZATION_ORDER",
    "RebuildFinalizationFreshnessError",
    "RebuildFinalizer",
]
