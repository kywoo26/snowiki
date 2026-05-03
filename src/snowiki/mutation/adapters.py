from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from snowiki.compiler.engine import CompilerEngine
from snowiki.search.retrieval_identity import retrieval_identity_for_tokenizer
from snowiki.search.runtime_identity import (
    current_runtime_index_formats,
    current_runtime_tokenizer_name,
)
from snowiki.search.runtime_retrieval import (
    build_retrieval_snapshot,
    clear_query_search_index_cache,
)
from snowiki.search.runtime_service import RetrievalSnapshot
from snowiki.storage.index_manifest import (
    IndexIdentity,
    RetrievalIdentity,
    current_index_identity,
    index_manifest_path,
    status_identity_payload,
)
from snowiki.storage.normalized import (
    MarkdownStoreResult,
    NormalizedStorage,
    StoreResult,
)
from snowiki.storage.provenance import RawRef
from snowiki.storage.raw import RawStorage
from snowiki.storage.zones import (
    StoragePaths,
    atomic_write_bytes,
    atomic_write_json,
    relative_to_root,
)


@dataclass(frozen=True, slots=True)
class MutationStorage:
    """Concrete raw, normalized, and filesystem operations used by mutations."""

    root: Path

    def store_raw_file(self, source_type: str, source_path: Path) -> RawRef:
        return RawStorage(self.root).store_file(source_type, source_path)

    def store_raw_bytes(
        self,
        source_type: str,
        content: bytes,
        *,
        source_name: str | None = None,
        mtime: datetime | float | int | None = None,
    ) -> RawRef:
        return RawStorage(self.root).store_bytes(
            source_type,
            content,
            source_name=source_name,
            mtime=mtime,
        )

    def store_markdown_document(
        self,
        *,
        source_root: str,
        relative_path: str,
        payload: dict[str, object],
        raw_ref: RawRef,
        recorded_at: datetime | str | None,
    ) -> MarkdownStoreResult:
        return NormalizedStorage(self.root).store_markdown_document(
            source_root=source_root,
            relative_path=relative_path,
            payload=payload,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def store_record(
        self,
        *,
        source_type: str,
        record_type: str,
        record_id: str,
        payload: dict[str, object],
        raw_ref: RawRef | Sequence[RawRef],
        recorded_at: datetime | str | None,
    ) -> StoreResult:
        return NormalizedStorage(self.root).store_record(
            source_type=source_type,
            record_type=record_type,
            record_id=record_id,
            payload=payload,
            raw_ref=raw_ref,
            recorded_at=recorded_at,
        )

    def write_bytes(self, relative_path: str, content: bytes) -> str:
        root = self.root.expanduser().resolve()
        target = (root / relative_path).resolve()
        _ = relative_to_root(root, target)
        written = atomic_write_bytes(target, content)
        return relative_to_root(root, written)

    def write_json(self, relative_path: str, payload: object) -> str:
        root = self.root.expanduser().resolve()
        target = (root / relative_path).resolve()
        _ = relative_to_root(root, target)
        written = atomic_write_json(target, payload)
        return relative_to_root(root, written)

    def delete_relative_path(self, relative_path: str) -> str:
        root = self.root.expanduser().resolve()
        target = (root / relative_path).resolve()
        _ = relative_to_root(root, target)
        target.unlink()
        return relative_to_root(root, target)


@dataclass(frozen=True, slots=True)
class CompiledPageAdapter:
    """Concrete adapter for compiler-owned page generation."""

    root: Path

    def rebuild_compiled_pages(self) -> tuple[str, ...]:
        return tuple(CompilerEngine(self.root).rebuild())


@dataclass(frozen=True, slots=True)
class RetrievalAdapter:
    """Concrete adapter for retrieval cache and snapshot operations."""

    root: Path

    def clear_query_cache(self) -> None:
        clear_query_search_index_cache()

    def build_snapshot(self) -> RetrievalSnapshot:
        return build_retrieval_snapshot(self.root)


@dataclass(frozen=True, slots=True)
class IndexManifestAdapter:
    """Concrete adapter for index identity and manifest persistence."""

    root: Path

    @property
    def paths(self) -> StoragePaths:
        return StoragePaths(self.root)

    def current_tokenizer_name(self) -> str:
        return current_runtime_tokenizer_name()

    def retrieval_identity(self, tokenizer_name: str) -> RetrievalIdentity:
        return retrieval_identity_for_tokenizer(tokenizer_name)

    def current_index_formats(self) -> tuple[str, str]:
        return current_runtime_index_formats()

    def current_identity(
        self,
        retrieval_identity: RetrievalIdentity,
        *,
        search_document_format: str,
        lexical_index_format: str,
    ) -> IndexIdentity:
        return current_index_identity(
            self.paths,
            retrieval_identity,
            search_document_format=search_document_format,
            lexical_index_format=lexical_index_format,
        )

    def status_identity_payload(self, identity: IndexIdentity) -> dict[str, object]:
        return status_identity_payload(identity)

    def manifest_relative_path(self) -> str:
        path = index_manifest_path(self.paths)
        return path.relative_to(self.paths.root).as_posix()

type ContentIdentity = Mapping[str, object]


__all__ = [
    "CompiledPageAdapter",
    "ContentIdentity",
    "IndexManifestAdapter",
    "MutationStorage",
    "RetrievalAdapter",
]
