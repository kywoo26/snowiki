from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CompilerEngine = importlib.import_module("snowiki.compiler.engine").CompilerEngine
NormalizedStorage = importlib.import_module(
    "snowiki.storage.normalized"
).NormalizedStorage


def test_compiled_pages_preserve_provenance_backlinks(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)
    storage.store_record(
        source_type="claude",
        record_type="message",
        record_id="msg-1",
        payload={
            "session_id": "session-9",
            "title": "Trace raw inputs",
            "summary": "Connected compiled pages back to the raw capture.",
            "concepts": ["Provenance Links"],
        },
        raw_ref={
            "sha256": "feedbeef",
            "path": "raw/claude/fe/edbeef",
            "size": 91,
            "mtime": "2026-04-08T15:00:00Z",
        },
        recorded_at="2026-04-08T15:00:00Z",
    )

    compiler = CompilerEngine(tmp_path)
    compiler.rebuild()

    concept_page = tmp_path / "compiled" / "concepts" / "provenance-links.md"
    summary_pages = sorted((tmp_path / "compiled" / "summaries").glob("*.md"))

    concept_content = concept_page.read_text(encoding="utf-8")
    summary_content = summary_pages[0].read_text(encoding="utf-8")

    assert "## Provenance" in concept_content
    assert "`raw/claude/fe/edbeef`" in concept_content
    assert "sha256: feedbeef" in concept_content
    assert "[[compiled/overview]]" in concept_content
    assert "## Provenance" in summary_content
    assert "`raw/claude/fe/edbeef`" in summary_content
