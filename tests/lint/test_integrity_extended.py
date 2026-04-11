from __future__ import annotations

import json
from pathlib import Path

import pytest

from snowiki.lint import integrity


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_check_layer_integrity_reports_missing_provenance_and_compiled_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_json(tmp_path / "normalized" / "record.json", {"provenance": {}})
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert result["root"] == tmp_path.as_posix()
    assert result["error_count"] == 2
    assert result["issues"] == [
        {
            "code": "L101",
            "severity": "error",
            "path": "normalized/record.json",
            "message": "normalized record missing raw provenance",
        },
        {
            "code": "L103",
            "severity": "error",
            "path": "compiled",
            "message": "compiled layer missing for existing normalized records",
        },
    ]


def test_check_layer_integrity_reports_missing_raw_targets_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_json(
        tmp_path / "normalized" / "record.json",
        {"provenance": {"raw_refs": [{"path": "raw/claude/missing.jsonl"}]}},
    )
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    monkeypatch.setattr(
        integrity,
        "find_stale_wikilinks",
        lambda base: [
            {
                "code": "L201",
                "severity": "warning",
                "path": "compiled/topic.md",
                "message": "stale",
            }
        ],
    )
    monkeypatch.setattr(
        integrity,
        "find_orphaned_compiled_pages",
        lambda base: [
            {
                "code": "L202",
                "severity": "warning",
                "path": "compiled/topic.md",
                "message": "orphaned",
            }
        ],
    )

    result = integrity.check_layer_integrity(tmp_path)

    assert result["error_count"] == 2
    assert result["issues"] == [
        {
            "code": "L102",
            "severity": "error",
            "path": "normalized/record.json",
            "message": "raw provenance target missing: raw/claude/missing.jsonl",
        },
        {
            "code": "L104",
            "severity": "error",
            "path": "index/manifest.json",
            "message": "index manifest missing for compiled layer",
        },
        {
            "code": "L201",
            "severity": "warning",
            "path": "compiled/topic.md",
            "message": "stale",
        },
        {
            "code": "L202",
            "severity": "warning",
            "path": "compiled/topic.md",
            "message": "orphaned",
        },
    ]


def test_check_layer_integrity_returns_clean_result_for_healthy_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "raw" / "claude" / "fixture.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("{}\n", encoding="utf-8")
    _write_json(
        tmp_path / "normalized" / "record.json",
        {"provenance": {"raw_refs": [{"path": "raw/claude/fixture.jsonl"}]}},
    )
    compiled_path = tmp_path / "compiled" / "topic.md"
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text("# Topic\n", encoding="utf-8")
    _write_json(tmp_path / "index" / "manifest.json", {"pages": ["topic.md"]})
    monkeypatch.setattr(integrity, "find_stale_wikilinks", lambda base: [])
    monkeypatch.setattr(integrity, "find_orphaned_compiled_pages", lambda base: [])

    result = integrity.check_layer_integrity(tmp_path)

    assert result == {"root": tmp_path.as_posix(), "issues": [], "error_count": 0}
