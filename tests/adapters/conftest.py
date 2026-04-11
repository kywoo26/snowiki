from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

pytest = import_module("pytest")


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def claude_fixture_dir() -> Path:
    return ROOT / "fixtures" / "claude"


@pytest.fixture
def unknown_claude_fixture(tmp_path: Path, claude_fixture_dir: Path) -> Path:
    fixture_path = tmp_path / "unknown-event.jsonl"
    lines = (
        (claude_fixture_dir / "basic.jsonl").read_text(encoding="utf-8").splitlines()
    )
    injected = json.dumps(
        {
            "record_type": "unknown_event",
            "session_id": "claude-basic",
            "event_id": "claude-basic-unknown-1",
            "created_at": "2026-04-08T12:00:15Z",
            "payload": {"note": "ignored by adapter"},
        }
    )
    lines.insert(2, injected)
    fixture_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return fixture_path
