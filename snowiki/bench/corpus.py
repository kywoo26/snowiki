from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from snowiki.cli.commands.ingest import run_ingest
from snowiki.cli.commands.rebuild import run_rebuild

_REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_BENCHMARK_FIXTURE_PATHS: dict[str, str] = {
    "claude_basic": "fixtures/claude/basic.jsonl",
    "claude_tools": "fixtures/claude/with_tools.jsonl",
    "claude_attachments": "fixtures/claude/with_attachments.jsonl",
    "claude_sidechains": "fixtures/claude/with_sidechains.jsonl",
    "claude_resumed": "fixtures/claude/resumed.jsonl",
    "claude_large_output": "fixtures/claude/large_output.jsonl",
    "claude_secret": "fixtures/claude/secret_bearing.jsonl",
    "omo_basic": "fixtures/opencode/basic.db",
    "omo_todos": "fixtures/opencode/with_todos.db",
    "omo_diffs": "fixtures/opencode/with_diffs.db",
    "omo_reasoning": "fixtures/opencode/with_reasoning.db",
    "omo_compaction": "fixtures/opencode/with_compaction.db",
}


@dataclass(frozen=True)
class BenchmarkFixture:
    fixture_id: str
    source: str
    path: Path


class SeededFixture(TypedDict):
    fixture_id: str
    source: str
    path: str


def canonical_benchmark_fixtures() -> tuple[BenchmarkFixture, ...]:
    return tuple(
        BenchmarkFixture(
            fixture_id=fixture_id,
            source="claude" if relative_path.endswith('.jsonl') else "opencode",
            path=_REPO_ROOT / relative_path,
        )
        for fixture_id, relative_path in CANONICAL_BENCHMARK_FIXTURE_PATHS.items()
    )


def seed_canonical_benchmark_root(root: Path) -> list[SeededFixture]:
    fixtures = canonical_benchmark_fixtures()
    for fixture in fixtures:
        _ = run_ingest(fixture.path, source=fixture.source, root=root)
    _ = run_rebuild(root)
    return [
        {
            "fixture_id": fixture.fixture_id,
            "source": fixture.source,
            "path": fixture.path.as_posix(),
        }
        for fixture in fixtures
    ]
