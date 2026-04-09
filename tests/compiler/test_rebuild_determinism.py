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


def test_rebuild_is_deterministic(tmp_path: Path) -> None:
    storage = NormalizedStorage(tmp_path)

    storage.store_record(
        source_type="claude",
        record_type="session",
        record_id="session-1",
        payload={
            "metadata": {"title": "Build Compiled Wiki Pipeline"},
            "summary": "Implemented the first compiled wiki pipeline from normalized storage.",
            "concepts": [
                {
                    "title": "Compiler Engine",
                    "summary": "Coordinates deterministic page rebuilds.",
                },
            ],
            "entities": [
                {
                    "title": "Snowiki",
                    "summary": "The project that owns the wiki graph.",
                },
            ],
            "topics": ["Deterministic Builds"],
            "questions": ["How should provenance backlinks work"],
            "projects": ["Wiki Compiler"],
            "decisions": ["Use normalized storage as compiler input"],
        },
        raw_ref={
            "sha256": "abc123",
            "path": "raw/claude/ab/c123",
            "size": 42,
            "mtime": "2026-04-08T12:00:00Z",
        },
        recorded_at="2026-04-08T12:00:00Z",
    )
    storage.store_record(
        source_type="claude",
        record_type="message",
        record_id="msg-1",
        payload={
            "session_id": "session-1",
            "title": "Deterministic rebuild pass",
            "summary": "Added stable slugs and cross-links for compiled pages.",
            "concepts": ["Compiler Engine"],
            "topics": ["Deterministic Builds"],
            "entities": ["Snowiki"],
        },
        raw_ref={
            "sha256": "def456",
            "path": "raw/claude/de/f456",
            "size": 24,
            "mtime": "2026-04-08T12:10:00Z",
        },
        recorded_at="2026-04-08T12:10:00Z",
    )

    compiler = CompilerEngine(tmp_path)

    first_paths = compiler.rebuild()
    first_snapshot = compiled_snapshot(tmp_path)
    second_paths = compiler.rebuild()
    second_snapshot = compiled_snapshot(tmp_path)

    assert first_paths == second_paths
    assert first_snapshot == second_snapshot
    assert "compiled/overview.md" in first_paths
    assert "compiled/concepts/compiler-engine.md" in first_paths
    assert "compiled/entities/snowiki.md" in first_paths
    assert "compiled/topics/deterministic-builds.md" in first_paths
    assert "compiled/questions/how-should-provenance-backlinks-work.md" in first_paths
    assert "compiled/projects/wiki-compiler.md" in first_paths
    assert (
        "compiled/decisions/use-normalized-storage-as-compiler-input.md" in first_paths
    )
    assert "compiled/sessions/session-1.md" in first_paths
    assert (
        len([path for path in first_paths if path.startswith("compiled/summaries/")])
        == 2
    )


def compiled_snapshot(root: Path) -> dict[str, str]:
    compiled_root = root / "compiled"
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(
            compiled_root.rglob("*.md"), key=lambda candidate: candidate.as_posix()
        )
    }
