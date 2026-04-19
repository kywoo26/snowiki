from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

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
VALID_DOC_IDS.update({
    "claude_secret",
    "benchmarks/queries.json",
    "benchmarks/judgments.json",
    "wiki-benchmark-overview",
    "wiki-mixed-search-overview",
})

JSONDict = dict[str, Any]


def _read_json(path: Path) -> JSONDict:
    return cast(JSONDict, json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[JSONDict]:
    return [
        cast(JSONDict, json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_expected_fixture_directories_exist(
    claude_fixtures_dir: Path,
    opencode_fixtures_dir: Path,
    corrupted_claude_fixtures_dir: Path,
    corrupted_opencode_fixtures_dir: Path,
    benchmarks_dir: Path,
) -> None:
    assert claude_fixtures_dir.is_dir()
    assert opencode_fixtures_dir.is_dir()
    assert corrupted_claude_fixtures_dir.is_dir()
    assert corrupted_opencode_fixtures_dir.is_dir()
    assert benchmarks_dir.is_dir()


def test_claude_fixture_inventory_and_provenance(
    claude_fixtures_dir: Path,
) -> None:
    actual = {path.name for path in claude_fixtures_dir.glob("*.jsonl")}
    assert actual == set(EXPECTED_CLAUDE)

    for filename, expected_id in EXPECTED_CLAUDE.items():
        records = _read_jsonl(claude_fixtures_dir / filename)
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

    large_output = claude_fixtures_dir / "large_output.jsonl"
    assert large_output.stat().st_size >= 10_000

    secret_text = (claude_fixtures_dir / "secret_bearing.jsonl").read_text(
        encoding="utf-8"
    )
    assert "sk-test-" in secret_text
    assert "ghp_" in secret_text
    assert "password" in secret_text.lower()


def test_corrupted_claude_inventory(
    corrupted_claude_fixtures_dir: Path,
) -> None:
    actual = {path.name for path in corrupted_claude_fixtures_dir.glob("*.jsonl")}
    assert actual == EXPECTED_CORRUPTED_CLAUDE

    missing_fields_records = _read_jsonl(
        corrupted_claude_fixtures_dir / "missing_fields.jsonl"
    )
    assert (
        missing_fields_records[0]["fixture"]["fixture_id"]
        == "corrupt_claude_missing_fields"
    )

    invalid_text = (corrupted_claude_fixtures_dir / "invalid_json.jsonl").read_text(
        encoding="utf-8"
    )
    assert invalid_text.count("\n") == 2
    assert invalid_text.rstrip().endswith('"This line is intentionally broken"')

    unknown_records = _read_jsonl(
        corrupted_claude_fixtures_dir / "unknown_event_type.jsonl"
    )
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


def test_opencode_fixture_inventory_and_structure(
    opencode_fixtures_dir: Path,
) -> None:
    actual = {path.name for path in opencode_fixtures_dir.glob("*.db")}
    assert actual == set(EXPECTED_OPENCODE)

    for filename, expected_id in EXPECTED_OPENCODE.items():
        path = opencode_fixtures_dir / filename
        tables = _fetch_sqlite_tables(path)
        assert {"project", "session", "message", "part", "fixture_provenance"}.issubset(
            tables
        )
        fixture_id, family = _fetch_fixture_provenance(path)
        assert fixture_id == expected_id
        assert family == "opencode_sqlite"

    conn = sqlite3.connect(opencode_fixtures_dir / "with_todos.db")
    try:
        todo_count = conn.execute("SELECT COUNT(*) FROM todo").fetchone()[0]
    finally:
        conn.close()
    assert todo_count > 0

    conn = sqlite3.connect(opencode_fixtures_dir / "with_diffs.db")
    try:
        diff_rows = conn.execute(
            'SELECT COUNT(*) FROM part WHERE data LIKE \'%"type": "diff"%\' OR data LIKE \'%"type":"diff"%\''
        ).fetchone()[0]
    finally:
        conn.close()
    assert diff_rows > 0

    conn = sqlite3.connect(opencode_fixtures_dir / "with_reasoning.db")
    try:
        reasoning_rows = conn.execute(
            "SELECT COUNT(*) FROM part WHERE data LIKE '%reasoning%'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert reasoning_rows > 0

    conn = sqlite3.connect(opencode_fixtures_dir / "with_compaction.db")
    try:
        compacting = conn.execute(
            "SELECT time_compacting FROM session LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert compacting is not None


def test_corrupted_opencode_inventory(
    corrupted_opencode_fixtures_dir: Path,
) -> None:
    actual = {path.name for path in corrupted_opencode_fixtures_dir.glob("*.db")}
    assert actual == EXPECTED_CORRUPTED_OPENCODE

    for stem in ["locked", "partial_rows", "schema_mismatch"]:
        provenance = corrupted_opencode_fixtures_dir / f"{stem}.provenance.json"
        assert provenance.exists()
        data = _read_json(provenance)
        assert data["created"]
        assert data["updated"]
        assert data["sources"]


def test_benchmark_query_and_judgment_inventory(
    benchmark_queries_path: Path,
    benchmark_judgments_path: Path,
) -> None:
    queries = _read_json(benchmark_queries_path)
    judgments = _read_json(benchmark_judgments_path)

    for payload in (queries, judgments):
        metadata = payload["metadata"]
        assert metadata["created"]
        assert metadata["updated"]
        assert metadata["sources"]

    query_items = queries["queries"]
    assert len(query_items) == 90

    groups = {"ko": 0, "en": 0, "mixed": 0}
    ids = []
    for item in query_items:
        ids.append(item["id"])
        groups[item["group"]] += 1
        assert item["kind"] in {"known-item", "topical", "temporal"}
        assert item["text"]

    assert groups == {"ko": 30, "en": 30, "mixed": 30}
    assert len(set(ids)) == 90

    gold = judgments["judgments"]
    canonical_query_ids = {
        item["id"] for item in query_items if item["group"] in {"ko", "mixed"}
    }
    canonical_judgment_ids = {
        query_id for query_id in gold if query_id.startswith(("ko-", "mix-"))
    }
    assert len(canonical_query_ids) == 60
    assert len(canonical_judgment_ids) == 60
    assert canonical_query_ids == canonical_judgment_ids
    assert set(ids) == set(gold)
    query_lookup = {item["id"]: item for item in query_items}
    tagged_queries = [item for item in query_items if item.get("tags")]
    no_answer_queries = [item for item in query_items if item.get("no_answer") is True]
    assert len(tagged_queries) >= 18
    assert len(no_answer_queries) >= 5
    for query_id, relevant_doc_ids in gold.items():
        assert query_id
        query = query_lookup[query_id]
        if query.get("no_answer") is True:
            assert relevant_doc_ids == []
        else:
            assert relevant_doc_ids
            assert set(relevant_doc_ids).issubset(VALID_DOC_IDS)
