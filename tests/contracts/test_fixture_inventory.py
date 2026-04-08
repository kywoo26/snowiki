from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
CLAUDE = FIXTURES / "claude"
CORRUPTED_CLAUDE = FIXTURES / "corrupted" / "claude"
OPENCODE = FIXTURES / "opencode"
CORRUPTED_OPENCODE = FIXTURES / "corrupted" / "opencode"
BENCHMARKS = ROOT / "benchmarks"

EXPECTED_CLAUDE = {
    "basic.jsonl": "claude_basic",
    "with_tools.jsonl": "claude_tools",
    "with_attachments.jsonl": "claude_attachments",
    "with_sidechains.jsonl": "claude_sidechains",
    "resumed.jsonl": "claude_resumed",
    "large_output.jsonl": "claude_large_output",
    "secret_bearing.jsonl": "claude_secret",
}

EXPECTED_CORRUPTED_CLAUDE = {
    "missing_fields.jsonl",
    "invalid_json.jsonl",
    "unknown_event_type.jsonl",
}

EXPECTED_OPENCODE = {
    "basic.db": "omo_basic",
    "with_todos.db": "omo_todos",
    "with_diffs.db": "omo_diffs",
    "with_reasoning.db": "omo_reasoning",
    "with_compaction.db": "omo_compaction",
}

EXPECTED_CORRUPTED_OPENCODE = {
    "locked.db",
    "partial_rows.db",
    "schema_mismatch.db",
}

VALID_DOC_IDS = set(EXPECTED_CLAUDE.values()) | set(EXPECTED_OPENCODE.values())
VALID_DOC_IDS.add("claude_secret")

JSONDict = dict[str, Any]


def _read_json(path: Path) -> JSONDict:
    return cast(JSONDict, json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[JSONDict]:
    return [
        cast(JSONDict, json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_expected_fixture_directories_exist() -> None:
    assert CLAUDE.is_dir()
    assert OPENCODE.is_dir()
    assert CORRUPTED_CLAUDE.is_dir()
    assert CORRUPTED_OPENCODE.is_dir()
    assert BENCHMARKS.is_dir()


def test_claude_fixture_inventory_and_provenance() -> None:
    actual = {path.name for path in CLAUDE.glob("*.jsonl")}
    assert actual == set(EXPECTED_CLAUDE)

    for filename, expected_id in EXPECTED_CLAUDE.items():
        records = _read_jsonl(CLAUDE / filename)
        assert records, filename
        provenance = records[0]
        if provenance["type"] == "system":
            assert provenance["subtype"] == "fixture_provenance"
            fixture = provenance["fixture"]
            assert fixture["fixture_id"] == expected_id
            assert fixture["created"]
            assert fixture["updated"]
            assert fixture["sources"]
            continue

        assert provenance["type"] == "session"
        assert provenance["session_id"]
        assert provenance["started_at"]
        metadata = cast(JSONDict, provenance["metadata"])
        assert metadata["fixture_family"] == "claude"

    large_output = CLAUDE / "large_output.jsonl"
    assert large_output.stat().st_size >= 10_000

    secret_text = (CLAUDE / "secret_bearing.jsonl").read_text(encoding="utf-8")
    assert "sk-test-" in secret_text
    assert "ghp_" in secret_text
    assert "password" in secret_text.lower()


def test_corrupted_claude_inventory() -> None:
    actual = {path.name for path in CORRUPTED_CLAUDE.glob("*.jsonl")}
    assert actual == EXPECTED_CORRUPTED_CLAUDE

    missing_fields_records = _read_jsonl(CORRUPTED_CLAUDE / "missing_fields.jsonl")
    assert (
        missing_fields_records[0]["fixture"]["fixture_id"]
        == "corrupt_claude_missing_fields"
    )

    invalid_text = (CORRUPTED_CLAUDE / "invalid_json.jsonl").read_text(encoding="utf-8")
    assert invalid_text.count("\n") == 2
    assert invalid_text.rstrip().endswith('"This line is intentionally broken"')

    unknown_records = _read_jsonl(CORRUPTED_CLAUDE / "unknown_event_type.jsonl")
    assert unknown_records[-1]["type"] == "teleport"


def _fetch_sqlite_tables(path: Path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def _fetch_fixture_provenance(path: Path) -> tuple[str, str]:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT fixture_id, family FROM fixture_provenance LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return row[0], row[1]


def test_opencode_fixture_inventory_and_structure() -> None:
    actual = {path.name for path in OPENCODE.glob("*.db")}
    assert actual == set(EXPECTED_OPENCODE)

    for filename, expected_id in EXPECTED_OPENCODE.items():
        path = OPENCODE / filename
        tables = _fetch_sqlite_tables(path)
        assert {"project", "session", "message", "part", "fixture_provenance"}.issubset(
            tables
        )
        fixture_id, family = _fetch_fixture_provenance(path)
        assert fixture_id == expected_id
        assert family == "opencode_sqlite"

    conn = sqlite3.connect(OPENCODE / "with_todos.db")
    try:
        todo_count = conn.execute("SELECT COUNT(*) FROM todo").fetchone()[0]
    finally:
        conn.close()
    assert todo_count > 0

    conn = sqlite3.connect(OPENCODE / "with_diffs.db")
    try:
        diff_rows = conn.execute(
            'SELECT COUNT(*) FROM part WHERE data LIKE \'%"type": "diff"%\' OR data LIKE \'%"type":"diff"%\''
        ).fetchone()[0]
    finally:
        conn.close()
    assert diff_rows > 0

    conn = sqlite3.connect(OPENCODE / "with_reasoning.db")
    try:
        reasoning_rows = conn.execute(
            "SELECT COUNT(*) FROM part WHERE data LIKE '%reasoning%'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert reasoning_rows > 0

    conn = sqlite3.connect(OPENCODE / "with_compaction.db")
    try:
        compacting = conn.execute(
            "SELECT time_compacting FROM session LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert compacting is not None


def test_corrupted_opencode_inventory() -> None:
    actual = {path.name for path in CORRUPTED_OPENCODE.glob("*.db")}
    assert actual == EXPECTED_CORRUPTED_OPENCODE

    for stem in ["locked", "partial_rows", "schema_mismatch"]:
        provenance = CORRUPTED_OPENCODE / f"{stem}.provenance.json"
        assert provenance.exists()
        data = _read_json(provenance)
        assert data["created"]
        assert data["updated"]
        assert data["sources"]


def test_benchmark_query_and_judgment_inventory() -> None:
    queries = _read_json(BENCHMARKS / "queries.json")
    judgments = _read_json(BENCHMARKS / "judgments.json")

    for payload in (queries, judgments):
        metadata = payload["metadata"]
        assert metadata["created"]
        assert metadata["updated"]
        assert metadata["sources"]

    query_items = queries["queries"]
    assert len(query_items) == 60

    groups = {"ko": 0, "en": 0, "mixed": 0}
    ids = []
    for item in query_items:
        ids.append(item["id"])
        groups[item["group"]] += 1
        assert item["kind"] in {"known-item", "topical", "temporal"}
        assert item["text"]

    assert groups == {"ko": 20, "en": 20, "mixed": 20}
    assert len(set(ids)) == 60

    gold = judgments["judgments"]
    assert set(ids) == set(gold)
    for query_id, relevant_doc_ids in gold.items():
        assert query_id
        assert relevant_doc_ids
        assert set(relevant_doc_ids).issubset(VALID_DOC_IDS)
