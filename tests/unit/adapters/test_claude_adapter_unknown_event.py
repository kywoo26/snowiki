from __future__ import annotations

from pathlib import Path

from snowiki.adapters import parse_claude_jsonl


def test_parser_keeps_unknown_records(unknown_claude_fixture: Path) -> None:
    records = parse_claude_jsonl(unknown_claude_fixture)

    assert records[2]["record_type"] == "unknown_event"
    assert records[2]["_line_number"] == 3


def test_parser_keeps_unknown_records_without_mutating_neighboring_rows(
    unknown_claude_fixture: Path,
) -> None:
    records = parse_claude_jsonl(unknown_claude_fixture)

    assert records[1]["record_type"] == "user"
    assert records[2]["record_type"] == "unknown_event"
    assert records[3]["record_type"] == "assistant"
    assert records[2]["payload"] == {"note": "ignored by adapter"}
