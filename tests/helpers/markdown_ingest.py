from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from snowiki.markdown.ingest import run_markdown_ingest

DEFAULT_RECORDED_AT = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)


def write_markdown_source(
    root: Path,
    *,
    name: str = "basic",
    title: str = "claude-basic",
    body: str = "claude-basic durable Markdown fixture.",
    recorded_at: datetime = DEFAULT_RECORDED_AT,
) -> Path:
    source_dir = root / "source-fixtures"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / f"{name}.md"
    _ = source_path.write_text(
        f"---\ntitle: {title}\nsummary: {body}\n---\n# {title}\n\n{body}\n",
        encoding="utf-8",
    )
    timestamp = recorded_at.timestamp()
    os.utime(source_path, (timestamp, timestamp))
    return source_path


def ingest_markdown_fixture(
    root: Path,
    *,
    name: str = "basic",
    title: str = "claude-basic",
    body: str = "claude-basic durable Markdown fixture.",
    recorded_at: datetime = DEFAULT_RECORDED_AT,
) -> Path:
    source_path = write_markdown_source(
        root,
        name=name,
        title=title,
        body=body,
        recorded_at=recorded_at,
    )
    _ = run_markdown_ingest(source_path, root=root)
    return source_path
