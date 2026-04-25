from __future__ import annotations

from pathlib import Path
from typing import NotRequired, Protocol, TypedDict

from snowiki.privacy import PrivacyGate
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.search.workspace import clear_query_search_index_cache
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.provenance import RawRef
from snowiki.storage.raw import RawStorage

from .discovery import MarkdownSource, discover_markdown_sources
from .frontmatter import FrontmatterValue, MarkdownDocument, parse_markdown_document


class MarkdownIngestDocumentResult(TypedDict):
    """Serialized result for one ingested Markdown document."""

    relative_path: str
    record_id: str
    content_hash: str
    status: str
    normalized_path: str
    raw_path: str


class MarkdownIngestResult(TypedDict):
    """Serialized result for a Markdown ingest operation."""

    root: str
    source_root: str
    documents_seen: int
    documents_inserted: int
    documents_updated: int
    documents_unchanged: int
    documents_stale: int
    rebuild_required: bool
    documents: list[MarkdownIngestDocumentResult]
    rebuild: NotRequired[dict[str, object]]


class SourcePrivacyGate(Protocol):
    """Source-path privacy boundary required by Markdown ingest."""

    def ensure_allowed_source(self, source_path: str | Path) -> None:
        """Raise when a source path must not be ingested."""


def resolve_markdown_title(
    source: MarkdownSource,
    document_text: str,
    promoted: dict[str, FrontmatterValue],
) -> str:
    """Return the effective title for a Markdown source."""
    title = promoted.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    for line in document_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return source.path.stem


def resolve_markdown_summary(promoted: dict[str, FrontmatterValue]) -> str:
    """Return the effective summary for a Markdown source."""
    for key in ("summary", "description"):
        value = promoted.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def ingest_markdown_source(
    source: MarkdownSource,
    *,
    raw_storage: RawStorage,
    normalized_storage: NormalizedStorage,
    privacy_gate: SourcePrivacyGate | None = None,
) -> MarkdownIngestDocumentResult:
    """Store one Markdown source through raw and normalized storage."""
    gate = privacy_gate or PrivacyGate()
    gate.ensure_allowed_source(source.path)
    raw_ref = raw_storage.store_file("markdown", source.path)
    content = source.path.read_text(encoding="utf-8")
    parsed = parse_markdown_document(content)
    payload = build_markdown_payload(source, parsed, raw_ref)
    result = normalized_storage.store_markdown_document(
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


def build_markdown_payload(
    source: MarkdownSource,
    document: MarkdownDocument,
    raw_ref: RawRef,
) -> dict[str, object]:
    """Build the normalized payload for a parsed Markdown source."""
    return {
        "title": resolve_markdown_title(source, document.text, document.promoted),
        "summary": resolve_markdown_summary(document.promoted),
        "text": document.text,
        "frontmatter": document.frontmatter,
        "promoted_frontmatter": document.promoted,
        "reserved_frontmatter": document.reserved,
        "source_path": source.path.as_posix(),
        "source_root": source.source_root.as_posix(),
        "relative_path": source.relative_path,
        "content_hash": str(raw_ref["sha256"]),
        "source_metadata": {
            "extension": source.path.suffix.lower(),
            "size": raw_ref["size"],
        },
    }


def run_markdown_ingest(
    path: Path,
    *,
    root: Path,
    source_root: Path | None = None,
    rebuild: bool = False,
    privacy_gate: SourcePrivacyGate | None = None,
) -> MarkdownIngestResult:
    """Ingest a Markdown file or directory into Snowiki storage."""
    gate = privacy_gate or PrivacyGate()
    gate.ensure_allowed_source(path)
    sources = discover_markdown_sources(path, source_root=source_root)
    raw_storage = RawStorage(root)
    normalized_storage = NormalizedStorage(root)
    documents = [
        ingest_markdown_source(
            source,
            raw_storage=raw_storage,
            normalized_storage=normalized_storage,
            privacy_gate=gate,
        )
        for source in sources
    ]
    source_root_value = (
        sources[0].source_root.as_posix() if sources else path.resolve().as_posix()
    )
    result: MarkdownIngestResult = {
        "root": root.as_posix(),
        "source_root": source_root_value,
        "documents_seen": len(documents),
        "documents_inserted": _count_documents_by_status(documents, "inserted"),
        "documents_updated": _count_documents_by_status(documents, "updated"),
        "documents_unchanged": _count_documents_by_status(documents, "unchanged"),
        "documents_stale": 0,
        "rebuild_required": bool(documents),
        "documents": documents,
    }
    if rebuild:
        result["rebuild"] = _run_rebuild(root)
        result["rebuild_required"] = False
    clear_query_search_index_cache()
    return result


def _count_documents_by_status(
    documents: list[MarkdownIngestDocumentResult],
    status: str,
) -> int:
    return sum(1 for document in documents if document["status"] == status)


def _run_rebuild(root: Path) -> dict[str, object]:
    return {"root": root.as_posix(), **run_rebuild_with_integrity(root)}
