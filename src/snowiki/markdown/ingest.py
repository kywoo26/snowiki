from __future__ import annotations

from pathlib import Path
from typing import NotRequired, Protocol, TypedDict

from snowiki.compiler.projection import (
    ProjectionSection,
    SourceIdentity,
    make_compiler_projection,
)
from snowiki.markdown.source_state import count_stale_markdown_sources
from snowiki.privacy import PrivacyGate
from snowiki.rebuild.integrity import run_rebuild_with_integrity
from snowiki.search.runtime_retrieval import clear_query_search_index_cache
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
    document: MarkdownDocument,
) -> str:
    """Return the effective title for a Markdown source."""
    title = document.promoted.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    if document.structure.headings:
        return document.structure.headings[0].text
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
    title = resolve_markdown_title(source, document)
    summary = resolve_markdown_summary(document.promoted)
    tags = _promoted_tags(document.promoted)
    source_identity: SourceIdentity = {
        "source_root": source.source_root.as_posix(),
        "relative_path": source.relative_path,
        "content_hash": str(raw_ref["sha256"]),
    }
    projection = make_compiler_projection(
        title=title,
        summary=summary,
        body=document.text,
        tags=tags,
        source_identity=source_identity,
        sections=_projection_sections(document),
    )
    return {
        "title": title,
        "summary": summary,
        "text": document.text,
        "frontmatter": document.frontmatter,
        "promoted_frontmatter": document.promoted,
        "reserved_frontmatter": document.reserved,
        "projection": projection,
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
        "documents_stale": count_stale_markdown_sources(
            root, source_root=source_root_value, include_untracked=False
        ),
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


def _promoted_tags(promoted: dict[str, FrontmatterValue]) -> list[str]:
    tags = promoted.get("tags")
    if not isinstance(tags, list):
        return []
    return sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()})


def _projection_sections(document: MarkdownDocument) -> list[ProjectionSection]:
    sections: list[ProjectionSection] = [
        {"title": section.title, "body": section.body}
        for section in document.structure.sections
        if section.body.strip()
    ]
    if sections:
        return sections
    if document.text:
        return [{"title": "Document", "body": document.text}]
    return []
