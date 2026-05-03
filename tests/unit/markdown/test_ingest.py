from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from tests.helpers.projection import compiler_projection

from snowiki.markdown.discovery import MarkdownSource
from snowiki.markdown.frontmatter import parse_markdown_document
from snowiki.markdown.ingest import (
    build_markdown_payload,
    ingest_markdown_source,
    resolve_markdown_summary,
    resolve_markdown_title,
    run_markdown_ingest,
)
from snowiki.storage.normalized import NormalizedStorage
from snowiki.storage.raw import RawStorage


def test_resolve_markdown_title_prefers_promoted_title(tmp_path: Path) -> None:
    source = _markdown_source(tmp_path, "note.md")
    document = parse_markdown_document("---\ntitle: Frontmatter Title\n---\n# Heading")

    assert resolve_markdown_title(source, document) == "Frontmatter Title"


def test_resolve_markdown_title_falls_back_to_heading_then_stem(
    tmp_path: Path,
) -> None:
    source = _markdown_source(tmp_path, "guide.md")

    assert (
        resolve_markdown_title(source, parse_markdown_document("\n## Guide Heading\nBody"))
        == "Guide Heading"
    )
    assert resolve_markdown_title(source, parse_markdown_document("Body only")) == "guide"


def test_resolve_markdown_title_uses_markdown_body_parser(tmp_path: Path) -> None:
    source = _markdown_source(tmp_path, "guide.md")
    document_text = "```python\n# Not a title\n```\n\nSetext Title\n============\n"

    assert resolve_markdown_title(source, parse_markdown_document(document_text)) == "Setext Title"


def test_resolve_markdown_summary_prefers_summary_then_description() -> None:
    assert resolve_markdown_summary({"summary": " Summary ", "description": "Desc"}) == "Summary"
    assert resolve_markdown_summary({"description": " Desc "}) == "Desc"
    assert resolve_markdown_summary({"summary": ""}) == ""


def test_ingest_markdown_source_builds_normalized_payload(tmp_path: Path) -> None:
    source = _markdown_source(tmp_path, "notes/guide.md")
    source.path.parent.mkdir(parents=True)
    _ = source.path.write_text(
        "---\ntitle: Guide\nsummary: Useful guide\ntags: [docs]\n---\n# Guide\n\nBody",
        encoding="utf-8",
    )
    raw_storage = RawStorage(tmp_path / "snowiki")
    normalized_storage = NormalizedStorage(tmp_path / "snowiki")

    result = ingest_markdown_source(
        source,
        raw_storage=raw_storage,
        normalized_storage=normalized_storage,
    )

    record = normalized_storage.read_record(result["normalized_path"])
    assert result["relative_path"] == "notes/guide.md"
    assert result["status"] == "inserted"
    assert record["title"] == "Guide"
    assert record["summary"] == "Useful guide"
    assert record["text"] == "# Guide\n\nBody"
    assert record["promoted_frontmatter"] == {
        "title": "Guide",
        "summary": "Useful guide",
        "tags": ["docs"],
    }
    assert record["source_metadata"] == {"extension": ".md", "size": source.path.stat().st_size}


def test_build_markdown_payload_isolated_from_storage(tmp_path: Path) -> None:
    source = _markdown_source(tmp_path, "guide.md")
    document = parse_markdown_document("---\ndescription: Helpful\n---\n# Guide\n\nBody")

    payload = build_markdown_payload(
        source,
        document,
        {
            "sha256": "abc123",
            "path": "raw/markdown/ab/c123",
            "size": 42,
            "mtime": "2026-04-01T00:00:00+00:00",
        },
    )

    assert payload["title"] == "Guide"
    assert payload["summary"] == "Helpful"
    assert payload["content_hash"] == "abc123"
    assert payload["source_metadata"] == {"extension": ".md", "size": 42}
    assert payload["projection"] == compiler_projection(
        "Guide",
        "Helpful",
        body="# Guide\n\nBody",
        source_identity={
            "source_root": tmp_path.as_posix(),
            "relative_path": "guide.md",
            "content_hash": "abc123",
        },
        sections=[{"title": "Guide", "body": "Body"}],
    )


def test_ingest_markdown_source_uses_injected_privacy_gate(tmp_path: Path) -> None:
    source = _markdown_source(tmp_path, "private.md")
    _ = source.path.write_text("# Private", encoding="utf-8")
    gate = BlockingPrivacyGate()

    with pytest.raises(ValueError, match="blocked by test gate"):
        _ = ingest_markdown_source(
            source,
            raw_storage=RawStorage(tmp_path / "snowiki"),
            normalized_storage=NormalizedStorage(tmp_path / "snowiki"),
            privacy_gate=gate,
        )

    assert gate.checked_paths == [source.path]


def test_run_markdown_ingest_aggregates_document_counts(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    _ = (docs / "one.md").write_text("# One", encoding="utf-8")
    _ = (docs / "two.md").write_text("# Two", encoding="utf-8")

    result = run_markdown_ingest(docs, root=tmp_path / "snowiki")

    assert result["source_root"] == docs.resolve().as_posix()
    assert result["documents_seen"] == 2
    assert result["documents_inserted"] == 2
    assert result["documents_updated"] == 0
    assert result["documents_unchanged"] == 0
    assert result["documents_stale"] == 0
    assert result["rebuild_required"] is True


def test_run_markdown_ingest_rebuilds_and_clears_cache(
    tmp_path: Path,
) -> None:
    note = tmp_path / "note.md"
    _ = note.write_text("# Note", encoding="utf-8")
    root = tmp_path / "snowiki"

    result = run_markdown_ingest(note, root=root, rebuild=True)

    assert result["rebuild_required"] is False
    assert "rebuild" in result
    rebuild_result = result["rebuild"]
    assert rebuild_result["root"] == root.resolve().as_posix()
    assert cast("int", rebuild_result["compiled_count"]) >= 1
    assert cast("int", rebuild_result["search_documents"]) >= 1


def test_run_markdown_ingest_uses_injected_privacy_gate_for_sources(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    blocked = docs / "private.md"
    _ = blocked.write_text("# Private", encoding="utf-8")
    gate = PathBlockingPrivacyGate(blocked)

    with pytest.raises(ValueError, match="blocked by test gate"):
        _ = run_markdown_ingest(
            docs,
            root=tmp_path / "snowiki",
            privacy_gate=gate,
        )

    assert gate.checked_paths == [docs, blocked]


class BlockingPrivacyGate:
    def __init__(self) -> None:
        self.checked_paths: list[Path] = []

    def ensure_allowed_source(self, source_path: str | Path) -> None:
        path = Path(source_path)
        self.checked_paths.append(path)
        raise ValueError("blocked by test gate")


class PathBlockingPrivacyGate:
    def __init__(self, blocked_path: Path) -> None:
        self.blocked_path = blocked_path
        self.checked_paths: list[Path] = []

    def ensure_allowed_source(self, source_path: str | Path) -> None:
        path = Path(source_path)
        self.checked_paths.append(path)
        if path == self.blocked_path:
            raise ValueError("blocked by test gate")


def _markdown_source(root: Path, relative_path: str) -> MarkdownSource:
    return MarkdownSource(
        path=root / relative_path,
        source_root=root,
        relative_path=relative_path,
    )
